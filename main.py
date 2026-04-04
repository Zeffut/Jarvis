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
import numpy as np
import sounddevice as sd

from config import (
    load_config,
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    CONVERSATION_TIMEOUT,
)
from wake_word import WakeWordListener
from transcriber import Transcriber
from assistant import Assistant, TOKEN, SENTENCE
from speaker import speak, preload_greeting, play_greeting
from audio import is_silent
import ui

PREVIEW_INTERVAL = 0.4  # seconds between preview transcriptions


class MicBuffer:
    """Keeps the mic open and buffers audio continuously."""

    def __init__(self):
        self.chunks: list[np.ndarray] = []
        self.speech_started = False
        self.silence_start: float | None = None
        self.done = False
        self._lock = threading.Lock()

    def callback(self, indata, frames, time_info, status):
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

        # Timeout check (only before speech starts)
        if timeout > 0 and not mic.speech_started and now - start >= timeout:
            return None

        # Preview transcription while recording
        if mic.speech_started and now - last_preview >= PREVIEW_INTERVAL:
            with mic._lock:
                chunk_count = len(mic.chunks)
            if chunk_count > last_chunk_count:
                audio = mic.get_audio()
                if audio is not None and len(audio) > 0:
                    last_preview = now
                    last_chunk_count = chunk_count
                    # Use tiny model for fast preview
                    segments, _ = preview_model.transcribe(
                        audio, language="fr", beam_size=1,
                    )
                    preview = "".join(seg.text for seg in segments).strip()
                    if preview:
                        ui.show_user_preview(preview)

    return mic.get_audio()


def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
    preview_model,
    elevenlabs_key: str,
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
        while True:
            timeout = 0 if first_turn else CONVERSATION_TIMEOUT

            audio = record_with_preview(mic, preview_model, timeout=timeout)
            first_turn = False

            if audio is None:
                break

            # Final accurate transcription with mlx-whisper turbo
            final_text = transcriber.transcribe(audio)
            if not final_text:
                break

            ui.show_user_text(final_text)
            ui.show_jarvis_start()

            # Queue sentences for TTS in background thread
            import queue
            tts_queue: queue.Queue[str | None] = queue.Queue()

            def tts_worker():
                while True:
                    sentence = tts_queue.get()
                    if sentence is None:
                        break
                    speak(sentence, api_key=elevenlabs_key)

            tts_thread = threading.Thread(target=tts_worker, daemon=True)
            tts_thread.start()

            for event_type, text in assistant.ask_stream(final_text):
                if event_type == TOKEN:
                    ui.show_jarvis_token(text)
                elif event_type == SENTENCE:
                    tts_queue.put(text)

            # Wait for TTS to finish
            tts_queue.put(None)
            tts_thread.join()

            ui.show_jarvis_end()
            mic.reset()

    ui.show_end_conversation()
    assistant.reset()


def main():
    ui.show_boot()

    cfg = load_config()

    ui.show_loading("Modele Whisper...")
    transcriber = Transcriber()

    ui.show_loading("Intelligence artificielle...")
    assistant = Assistant(api_key=cfg["anthropic_api_key"])

    ui.show_loading("Detection vocale...")
    wake = WakeWordListener()

    ui.show_loading("Synthese vocale...")
    preload_greeting(api_key=cfg["elevenlabs_api_key"])

    ui.show_ready()

    # Reuse wake word's tiny model for real-time preview
    preview_model = wake.model

    try:
        while True:
            ui.show_standby()
            wake.listen()
            ui.show_wake()
            play_greeting()
            conversation_loop(transcriber, assistant, preview_model, cfg["elevenlabs_api_key"])
    except KeyboardInterrupt:
        ui.show_shutdown()
    finally:
        wake.cleanup()


if __name__ == "__main__":
    main()
