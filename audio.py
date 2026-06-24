import numpy as np


def is_silent(audio_chunk: np.ndarray, threshold: float) -> bool:
    rms = np.sqrt(np.mean(audio_chunk**2))
    return bool(rms < threshold)
