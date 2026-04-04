from __future__ import annotations

import numpy as np
import sounddevice as sd

from audio import is_silent
from config import SAMPLE_RATE, SILENCE_THRESHOLD


WAKE_WORD = "jarvis"
# Listen in 0.5s chunks, accumulate up to 3s of speech before checking
CHUNK_DURATION = 0.5
MAX_LISTEN_SECONDS = 3.0
# Silence after speech to trigger transcription
WAKE_SILENCE_DURATION = 0.6


class WakeWordListener:
    def __init__(self, transcriber):
        self.transcriber = transcriber

    def listen(self) -> None:
        """Block until 'Jarvis' is detected via Whisper."""
        print("\n�� En écoute...")

        chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)

        while True:
            # Wait for speech (non-silent audio)
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=chunk_size,
            ) as stream:
                while True:
                    audio_frame, _ = stream.read(chunk_size)
                    if not is_silent(audio_frame[:, 0], SILENCE_THRESHOLD):
                        break

            # Speech detected — record until silence
            chunks: list[np.ndarray] = []
            silence_start: float | None = None

            import time

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=chunk_size,
            ) as stream:
                start = time.time()
                while time.time() - start < MAX_LISTEN_SECONDS:
                    audio_frame, _ = stream.read(chunk_size)
                    chunk = audio_frame[:, 0].copy()
                    chunks.append(chunk)

                    if is_silent(chunk, SILENCE_THRESHOLD):
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= WAKE_SILENCE_DURATION:
                            break
                    else:
                        silence_start = None

            if not chunks:
                continue

            audio = np.concatenate(chunks)
            text = self.transcriber.transcribe(audio).lower()

            if WAKE_WORD in text:
                print("🎙️  Je vous écoute...")
                return

    def cleanup(self) -> None:
        pass
