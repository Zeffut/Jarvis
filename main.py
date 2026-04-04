from __future__ import annotations

import sys
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
        """Wait until speech is recorded and silence detected. Returns None on timeout."""
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
    """Conversation with mic always open."""
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
            print("🎤 ...", end="", flush=True)

            result = mic.wait_for_speech(timeout=timeout)
            first_turn = False

            if result is None:
                print("\r   ", end="\r")
                break

            audio = mic.get_audio()
            if audio is None:
                break

            final_text = transcriber.transcribe(audio)
            print(f"\r💬 {final_text}   ")

            if not final_text:
                break

            print(f"🤖 ", end="", flush=True)

            # Stream Claude response and speak sentence by sentence
            # Mic stays open — captures user speech as soon as TTS ends
            for sentence in assistant.ask_stream(final_text):
                print(sentence, end=" ", flush=True)
                speak(sentence, api_key=elevenlabs_key)

            print()

            # Reset mic buffer for next turn — mic is still open
            mic.reset()

    assistant.reset()


def main():
    print("🚀 Jarvis démarre...")
    cfg = load_config()

    print("📦 Chargement du modèle Whisper...")
    transcriber = Transcriber()

    assistant = Assistant(api_key=cfg["anthropic_api_key"])

    print("📦 Chargement du modèle wake word...")
    wake = WakeWordListener()

    print("🔊 Pré-chargement de la voix...")
    preload_greeting(api_key=cfg["elevenlabs_api_key"])

    try:
        while True:
            wake.listen()
            play_greeting()
            conversation_loop(transcriber, assistant, cfg["elevenlabs_api_key"])
    except KeyboardInterrupt:
        print("\n👋 Jarvis s'éteint.")
    finally:
        wake.cleanup()


if __name__ == "__main__":
    main()
