import numpy as np
from faster_whisper import WhisperModel
from config import WHISPER_MODEL


class Transcriber:
    def __init__(self, model_size: str = WHISPER_MODEL):
        self.model = WhisperModel(model_size, compute_type="auto")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(audio, language="fr")
        text = "".join(seg.text for seg in segments).strip()
        return text
