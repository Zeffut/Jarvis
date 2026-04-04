from __future__ import annotations

import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from audio import is_silent
from config import SAMPLE_RATE, SILENCE_THRESHOLD


WAKE_VARIANTS = {"jarvis", "j'avis", "jarvisse", "gervis", "jarvi", "chavis", "gervais", "j'arrive"}
CHUNK_SAMPLES = int(SAMPLE_RATE * 0.2)  # 200ms chunks
MAX_RECORD_SECONDS = 1.5
WAKE_SILENCE_DURATION = 0.3


class WakeWordListener:
    def __init__(self):
        self.model = WhisperModel("tiny", compute_type="auto")

    def _transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            audio,
            language="fr",
            beam_size=1,
            initial_prompt="Jarvis",
            hotwords="Jarvis",
        )
        return "".join(seg.text for seg in segments).strip().lower()

    def listen(self) -> None:
        """Block until 'Jarvis' is detected."""
        print("\n🟢 En écoute...")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SAMPLES,
        ) as stream:
            while True:
                audio_frame, _ = stream.read(CHUNK_SAMPLES)
                chunk = audio_frame[:, 0]

                if is_silent(chunk, SILENCE_THRESHOLD):
                    continue

                # Speech detected — record short segment
                chunks = [chunk.copy()]
                silence_start = None
                start = time.time()

                while time.time() - start < MAX_RECORD_SECONDS:
                    audio_frame, _ = stream.read(CHUNK_SAMPLES)
                    c = audio_frame[:, 0].copy()
                    chunks.append(c)

                    if is_silent(c, SILENCE_THRESHOLD):
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= WAKE_SILENCE_DURATION:
                            break
                    else:
                        silence_start = None

                audio = np.concatenate(chunks)
                text = self._transcribe(audio)

                if any(v in text for v in WAKE_VARIANTS):
                    print("🎙️  Je vous écoute...")
                    return

    def cleanup(self) -> None:
        pass
