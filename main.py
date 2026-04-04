from __future__ import annotations

# Suppress all warnings and logs before any imports
import warnings
import os
import logging

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
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
from assistant import Assistant
from speaker import speak, preload_greeting, play_greeting
from audio import is_silent
import ui


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

    def wait_for_speech(self, timeout: float = 0) -> str | None:
        start = time.time()
        while not self.done:
            time.sleep(0.05)
            if timeout > 0 and not self.speech_started and time.time() - start >= timeout:
                return None
        with self._lock:
            if not self.chunks:
                return None
            return "ok"

    def get_audio(self) -> np.ndarray | None:
        with self._lock:
            if not self.chunks:
                return None
            return np.concatenate(self.chunks)


def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
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
            ui.show_listening()

            result = mic.wait_for_speech(timeout=timeout)
            first_turn = False

            if result is None:
                break

            audio = mic.get_audio()
            if audio is None:
                break

            final_text = transcriber.transcribe(audio)
            if not final_text:
                break

            ui.show_user_text(final_text)
            ui.show_jarvis_start()

            for sentence in assistant.ask_stream(final_text):
                ui.show_jarvis_token(sentence + " ")
                speak(sentence, api_key=elevenlabs_key)

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

    try:
        while True:
            ui.show_standby()
            wake.listen()
            ui.show_wake()
            play_greeting()
            conversation_loop(transcriber, assistant, cfg["elevenlabs_api_key"])
    except KeyboardInterrupt:
        ui.show_shutdown()
    finally:
        wake.cleanup()


if __name__ == "__main__":
    main()
