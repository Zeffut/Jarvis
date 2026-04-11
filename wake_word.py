from __future__ import annotations

import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from audio import is_silent
from config import SAMPLE_RATE, SILENCE_THRESHOLD


WAKE_VARIANTS = {"jarvis", "j'avis", "j'avais", "jarvisse", "gervis", "jarvi", "chavis", "gervais", "j'arrive", "j'en vis"}
CHUNK_SAMPLES = int(SAMPLE_RATE * 0.1)  # 100ms chunks
BUFFER_SECONDS = 1.5
BUFFER_SAMPLES = int(SAMPLE_RATE * BUFFER_SECONDS)
TRANSCRIBE_INTERVAL = 0.3  # transcribe every 300ms
LISTEN_TIMEOUT = 300.0     # 5 min max — évite boucle infinie si le modèle crash


class WakeWordListener:
    def __init__(self):
        self.model: WhisperModel | None = WhisperModel("tiny", compute_type="auto")

    def _transcribe(self, audio: np.ndarray) -> str:
        if self.model is None:
            return ""
        segments, _ = self.model.transcribe(
            audio,
            language="fr",
            beam_size=1,
            initial_prompt="Jarvis",
            hotwords="Jarvis",
        )
        return "".join(seg.text for seg in segments).strip().lower()

    def listen(self) -> None:
        """Block until 'Jarvis' is detected using rolling buffer."""
        buffer = np.zeros(BUFFER_SAMPLES, dtype=np.float32)
        has_speech = False
        last_transcribe = 0.0
        deadline = time.time() + LISTEN_TIMEOUT

        def callback(indata, frames, time_info, status):
            nonlocal buffer, has_speech
            chunk = indata[:, 0]
            n = len(chunk)
            if n >= len(buffer):
                buffer[:] = chunk[-len(buffer):]  # chunk anormalement large
            else:
                buffer[:-n] = buffer[n:]
                buffer[-n:] = chunk
            if not is_silent(chunk, SILENCE_THRESHOLD):
                has_speech = True

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SAMPLES,
            callback=callback,
        ):
            while True:
                time.sleep(0.05)

                if time.time() > deadline:
                    # Timeout de sécurité — relancer le cycle
                    deadline = time.time() + LISTEN_TIMEOUT

                now = time.time()
                if has_speech and now - last_transcribe >= TRANSCRIBE_INTERVAL:
                    has_speech = False
                    last_transcribe = now
                    text = self._transcribe(buffer.copy())

                    if any(v in text for v in WAKE_VARIANTS):
                        return

    def cleanup(self) -> None:
        """Libère le modèle Whisper tiny de la mémoire."""
        self.model = None
