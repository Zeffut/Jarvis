from __future__ import annotations

# Suppress all warnings and logs before any imports
import warnings
import os
import logging

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
logging.disable(logging.CRITICAL)

import time
import threading
import queue
import numpy as np
import sounddevice as sd

from config import (
    load_config,
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    CONVERSATION_TIMEOUT,
    END_SIGNAL,
)
from wake_word import WakeWordListener
from transcriber import Transcriber
from assistant import Assistant, TOKEN, SENTENCE, TOOL_USE
from speaker import speak, synthesize, preload_greeting, play_greeting, KOKORO_SAMPLE_RATE
from audio import is_silent
import jlog
import ui
import ui_socket

PREVIEW_INTERVAL = 0.08      # seconds between preview transcriptions
MAX_RECORDING_SECONDS = 120  # sécurité : arrêt même si speech continu
MAX_TRANSCRIBE_RETRIES = 3   # max "Pardon ?" avant de quitter


class MicBuffer:
    """Keeps the mic open and buffers audio continuously."""

    def __init__(self):
        self.chunks: list[np.ndarray] = []
        self.speech_started = False
        self.silence_start: float | None = None
        self.done = False
        self._muted = threading.Event()  # thread-safe : pas de race condition
        self._lock = threading.Lock()

    @property
    def muted(self) -> bool:
        return self._muted.is_set()

    @muted.setter
    def muted(self, value: bool) -> None:
        if value:
            self._muted.set()
        else:
            self._muted.clear()

    def callback(self, indata, frames, time_info, status):
        if self._muted.is_set():   # lecture atomique — thread-safe
            return
        chunk = indata[:, 0].copy()

        with self._lock:
            if not self.speech_started:
                if not is_silent(chunk, SILENCE_THRESHOLD):
                    self.speech_started = True
                    self.chunks.append(chunk)
                return

            self.chunks.append(chunk)

            if is_silent(chunk, SILENCE_THRESHOLD):
                if self.silence_start is None:
                    self.silence_start = time.time()
                elif time.time() - self.silence_start >= SILENCE_DURATION:
                    self.done = True
            else:
                self.silence_start = None

    def reset(self):
        with self._lock:
            self.chunks.clear()
            self.speech_started = False
            self.silence_start = None
            self.done = False

    def get_audio(self) -> np.ndarray | None:
        with self._lock:
            if not self.chunks:
                return None
            return np.concatenate(self.chunks)


def record_with_preview(mic: MicBuffer, preview_model, timeout: float = 0) -> np.ndarray | None:
    """Wait for speech with real-time preview transcription. Returns audio or None on timeout."""
    start = time.time()
    last_preview = 0.0
    last_chunk_count = 0

    ui.show_listening()

    while not mic.done:
        time.sleep(0.05)
        now = time.time()

        # Timeout avant parole
        if timeout > 0 and not mic.speech_started and now - start >= timeout:
            return None

        # Sécurité : enregistrement max 2 min même si speech continu
        if mic.speech_started and now - start >= MAX_RECORDING_SECONDS:
            mic.done = True
            break

        # Preview transcription while recording
        if mic.speech_started and now - last_preview >= PREVIEW_INTERVAL:
            with mic._lock:
                chunk_count = len(mic.chunks)
            if chunk_count > last_chunk_count:
                audio = mic.get_audio()
                if audio is not None and len(audio) > 0:
                    last_preview = now
                    last_chunk_count = chunk_count
                    # Fenêtre RMS : au moins 1600 samples pour être représentative
                    win = max(1600, len(audio) // 3)
                    rms = float(np.sqrt(np.mean(audio[-win:]**2)))
                    ui_socket.send_state("listening", rms)
                    # Use tiny model for fast preview
                    segments, _ = preview_model.transcribe(
                        audio, language="fr", beam_size=1,
                    )
                    preview = "".join(seg.text for seg in segments).strip()
                    if preview:
                        ui.show_user_preview(preview)

    return mic.get_audio()


def _is_source_line(text: str) -> bool:
    """Vrai si la phrase est une ligne de source/lien — pas à lire à voix haute."""
    t = text.strip()
    return (
        t.startswith("Sources") or
        t.startswith("- [") or
        t.startswith("[") and "](http" in t or
        t.startswith("http")
    )


def _tool_phrase(tool_name: str) -> str:
    """Retourne une courte phrase naturelle décrivant l'outil utilisé."""
    name = tool_name.lower()
    if "bash" in name:
        return "j'exécute"
    if "web_search" in name or "websearch" in name:
        return "je cherche en ligne"
    if "web_fetch" in name or "webfetch" in name or "fetch" in name:
        return "je consulte"
    if "read" in name:
        return "je lis"
    if "write" in name:
        return "j'écris"
    if "edit" in name:
        return "je modifie"
    if "glob" in name or "grep" in name:
        return "je cherche"
    if "agent" in name:
        return "je délègue"
    return "je travaille"


def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
    preview_model,
) -> None:
    mic = MicBuffer()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=int(SAMPLE_RATE * 0.1),
        callback=mic.callback,
    ):
        first_turn = True
        _transcribe_retries = 0
        while True:
            timeout = 0 if first_turn else CONVERSATION_TIMEOUT

            audio = record_with_preview(mic, preview_model, timeout=timeout)
            first_turn = False

            if audio is None:
                jlog.info("MAIN", "conversation end — audio timeout (no speech)")
                break

            # Final accurate transcription with mlx-whisper turbo
            t_w = time.time()
            final_text = transcriber.transcribe(audio)
            dt_w = time.time() - t_w
            audio_secs = len(audio) / SAMPLE_RATE
            if not final_text:
                _transcribe_retries += 1
                jlog.warn("WHISPER", f"empty transcription (audio={audio_secs:.1f}s, {dt_w:.2f}s) — retry {_transcribe_retries}/{MAX_TRANSCRIBE_RETRIES}")
                if _transcribe_retries >= MAX_TRANSCRIBE_RETRIES:
                    jlog.info("MAIN", "conversation end — too many transcribe failures")
                    break
                speak("Pardon ?")
                mic.reset()
                continue
            _transcribe_retries = 0
            jlog.info("WHISPER", f"({dt_w:.2f}s, audio={audio_secs:.1f}s): {jlog.trunc(final_text)}")

            ui.show_user_text(final_text)
            ui_socket.send_state("thinking")
            # Pipeline TTS deux étages : synthèse en avance pendant que l'audio joue
            synth_queue: queue.Queue[str | None] = queue.Queue()
            play_queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=2)
            end_conversation = False

            def synth_worker():
                """Thread 1 : synthétise (Kokoro) → met les samples dans play_queue."""
                while True:
                    sentence = synth_queue.get()
                    if sentence is None:
                        play_queue.put(None)
                        break
                    samples = synthesize(sentence)
                    try:
                        play_queue.put(samples, timeout=30)  # évite deadlock si play_worker crash
                    except queue.Full:
                        pass

            def play_worker():
                """Thread 2 : joue les samples dès qu'ils arrivent, sans attendre la synth."""
                while True:
                    samples = play_queue.get()
                    if samples is None:
                        break
                    ui_socket.send_state("speaking", 0.5)
                    mic.muted = True
                    sd.play(samples, samplerate=KOKORO_SAMPLE_RATE)
                    sd.wait()
                    time.sleep(0.25)  # laisser l'écho s'éteindre
                    mic.muted = False

            synth_thread = threading.Thread(target=synth_worker, daemon=True)
            play_thread = threading.Thread(target=play_worker, daemon=True)
            synth_thread.start()
            play_thread.start()

            # Collect full response, display tokens, queue sentences for TTS
            full_response  = ""
            display_buffer = ""

            try:
                jarvis_started = False
                for event_type, text in assistant.ask_stream(final_text):
                    if event_type == TOOL_USE:
                        import json as _json
                        tool_info = _json.loads(text)
                        tool_name = tool_info["name"]
                        ui.show_tool_use(tool_name, tool_info.get("description", ""))
                        synth_queue.put(_tool_phrase(tool_name))

                    elif event_type == TOKEN:
                        if not jarvis_started:
                            ui.show_jarvis_start()
                            jarvis_started = True
                        full_response  += text
                        display_buffer += text

                        if END_SIGNAL in display_buffer:
                            before = display_buffer.split(END_SIGNAL)[0]
                            if before:
                                ui.show_jarvis_token(before)
                            display_buffer  = ""
                            end_conversation = True
                            jlog.debug("MAIN", "[FIN] detected in stream tokens")
                        else:
                            ui.show_jarvis_token(display_buffer)
                            display_buffer = ""

                    elif event_type == SENTENCE:
                        clean = text.replace(END_SIGNAL, "").strip()
                        if clean and not _is_source_line(clean):
                            jlog.info("TTS", f"queue → {jlog.trunc(clean, 100)}")
                            synth_queue.put(clean)
                        if END_SIGNAL in text:
                            end_conversation = True
                            jlog.debug("MAIN", "[FIN] detected in sentence")

                if full_response.strip() == END_SIGNAL:
                    end_conversation = True
                    jlog.warn("MAIN", "Jarvis répond [FIN] tout seul — fin prématurée probable")

            finally:
                # Garantit le join même si exception
                synth_queue.put(None)
                synth_thread.join(timeout=10)
                play_thread.join(timeout=10)
                mic.reset()

            if end_conversation:
                jlog.info("MAIN", "conversation end — [FIN] received")
                break

    ui.show_end_conversation()
    ui_socket.send_state("standby")
    assistant.reset()


def main():
    jlog.info("MAIN", f"boot — pid={os.getpid()}")
    # Écrire le PID pour permettre à l'UI de tuer le processus proprement
    with open("/tmp/jarvis.pid", "w") as f:
        f.write(str(os.getpid()))

    ui.show_boot()

    load_config()

    ui.show_loading("Modele Whisper...")
    t0 = time.time()
    transcriber = Transcriber()
    jlog.info("WHISPER", f"loaded in {time.time() - t0:.2f}s")

    ui.show_loading("Claude Code...")
    t0 = time.time()
    assistant = Assistant()
    jlog.info("MAIN", f"Assistant init in {time.time() - t0:.2f}s")

    ui.show_loading("Detection vocale...")
    t0 = time.time()
    wake = WakeWordListener()
    jlog.info("WAKE", f"loaded in {time.time() - t0:.2f}s")
    ui_socket.launch_ui()

    ui.show_loading("Synthese vocale...")
    t0 = time.time()
    preload_greeting()
    jlog.info("TTS", f"Kokoro greeting preloaded in {time.time() - t0:.2f}s")

    ui.show_ready()
    jlog.info("MAIN", "ready — waiting for wake word")

    # Reuse wake word's tiny model for real-time preview
    preview_model = wake.model

    try:
        while True:
            ui.show_standby()
            wake.listen()
            jlog.info("WAKE", "wake word detected")
            ui_socket.send_state("listening")
            ui.show_wake()
            play_greeting()
            conversation_loop(transcriber, assistant, preview_model)
    except KeyboardInterrupt:
        jlog.info("MAIN", "KeyboardInterrupt — shutdown")
        ui.show_shutdown()
    finally:
        wake.cleanup()
        assistant.shutdown()
        try:
            os.unlink("/tmp/jarvis.pid")
        except OSError:
            pass
        jlog.info("MAIN", "exit")


if __name__ == "__main__":
    main()
