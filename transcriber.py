from __future__ import annotations

import tempfile
import os
import numpy as np
import soundfile as sf
import mlx_whisper

from config import WHISPER_MODEL


class Transcriber:
    def __init__(self, model: str = WHISPER_MODEL):
        self.model = model
        # Warm up the model on first load
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, np.zeros(16000, dtype=np.float32), 16000)
            mlx_whisper.transcribe(f.name, path_or_hf_repo=self.model, language="fr")
            os.unlink(f.name)

    def transcribe(self, audio: np.ndarray) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, 16000)
            result = mlx_whisper.transcribe(
                f.name,
                language="fr",
                path_or_hf_repo=self.model,
            )
            os.unlink(f.name)
        return result["text"].strip()
