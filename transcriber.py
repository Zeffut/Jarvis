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
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            sf.write(tmp.name, np.zeros(16000, dtype=np.float32), 16000)
            mlx_whisper.transcribe(tmp.name, path_or_hf_repo=self.model, language="fr")
        finally:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def transcribe(self, audio: np.ndarray) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            sf.write(tmp.name, audio, 16000)
            result = mlx_whisper.transcribe(
                tmp.name,
                language="fr",
                path_or_hf_repo=self.model,
            )
        finally:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        return result["text"].strip()
