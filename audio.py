import numpy as np
import sounddevice as sd
from config import SAMPLE_RATE


def is_silent(audio_chunk: np.ndarray, threshold: float) -> bool:
    rms = np.sqrt(np.mean(audio_chunk**2))
    return bool(rms < threshold)


def create_audio_stream(callback, sample_rate: int = SAMPLE_RATE) -> sd.InputStream:
    return sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=int(sample_rate * 0.1),
        callback=callback,
    )
