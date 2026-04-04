from __future__ import annotations

import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model

from config import SAMPLE_RATE


# openwakeword expects 16kHz, 16-bit, mono audio in 80ms chunks (1280 samples)
OWW_CHUNK_SIZE = 1280
DETECTION_THRESHOLD = 0.5


class WakeWordListener:
    def __init__(self):
        openwakeword.utils.download_models(["hey_jarvis_v0.1"])
        self.model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

    def listen(self) -> None:
        """Block until 'Hey Jarvis' is detected."""
        print("\n🟢 En écoute... (dis 'Hey Jarvis')")
        self.model.reset()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=OWW_CHUNK_SIZE,
        ) as stream:
            while True:
                audio_frame, _ = stream.read(OWW_CHUNK_SIZE)
                pcm = audio_frame.flatten()
                prediction = self.model.predict(pcm)

                for wake_word, score in prediction.items():
                    if score > DETECTION_THRESHOLD:
                        print("🎙️  Je vous écoute...")
                        return

    def cleanup(self) -> None:
        pass
