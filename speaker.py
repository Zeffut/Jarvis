from __future__ import annotations

import os
import subprocess
import warnings
import numpy as np
import sounddevice as sd

warnings.filterwarnings("ignore")

from config import KOKORO_VOICE, KOKORO_SPEED

_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".greeting_cache.npy")
_MODEL_REPO = "hexgrad/Kokoro-82M"
_MODEL_FILE = "kokoro-v0_19.onnx"
_VOICES_FILE = "voices.bin"
KOKORO_SAMPLE_RATE = 24000

_kokoro = None
_status_proc: subprocess.Popen | None = None
_greeting_samples: np.ndarray | None = None


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        from huggingface_hub import hf_hub_download
        model_path = hf_hub_download(repo_id=_MODEL_REPO, filename=_MODEL_FILE)
        voices_path = hf_hub_download(repo_id=_MODEL_REPO, filename=_VOICES_FILE)
        _kokoro = Kokoro(model_path, voices_path)
    return _kokoro


def _synthesize(text: str) -> np.ndarray:
    """Retourne des samples float32 à KOKORO_SAMPLE_RATE Hz."""
    kokoro = _get_kokoro()
    samples, _ = kokoro.create(
        text,
        voice=KOKORO_VOICE,
        speed=KOKORO_SPEED,
        lang="fr-fr",
    )
    return samples.astype(np.float32)


def preload_greeting() -> None:
    """Pré-génère 'Oui Monsieur ?' au démarrage pour lecture instantanée."""
    global _greeting_samples
    if os.path.exists(_CACHE_PATH):
        _greeting_samples = np.load(_CACHE_PATH)
        return
    _greeting_samples = _synthesize("Oui Monsieur ?")
    np.save(_CACHE_PATH, _greeting_samples)


def play_greeting() -> None:
    """Joue le greeting pré-caché."""
    if _greeting_samples is not None:
        sd.play(_greeting_samples, samplerate=KOKORO_SAMPLE_RATE)
        sd.wait()


def speak_status(text: str, voice: str = "Thomas") -> None:
    """Court statut vocal via TTS macOS natif (instantané, pas de modèle)."""
    global _status_proc
    if _status_proc and _status_proc.poll() is None:
        _status_proc.terminate()
    _status_proc = subprocess.Popen(
        ["say", "-v", voice, text],
        stderr=subprocess.DEVNULL,
    )


def speak(text: str, wait: bool = True) -> None:
    """Synthétise text via Kokoro et joue via sounddevice."""
    samples = _synthesize(text)
    sd.play(samples, samplerate=KOKORO_SAMPLE_RATE)
    if wait:
        sd.wait()
