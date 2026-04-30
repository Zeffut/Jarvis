from __future__ import annotations

import atexit
import os
import subprocess
import threading
import time
import warnings
import numpy as np
import sounddevice as sd

warnings.filterwarnings("ignore")

from config import KOKORO_VOICE, KOKORO_SPEED
import jlog

_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".greeting_cache.npy")
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
_MODEL_PATH = os.path.join(_MODELS_DIR, "kokoro-v1.0.onnx")
_VOICES_PATH = os.path.join(_MODELS_DIR, "voices-v1.0.bin")
_RELEASES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_SAMPLE_RATE = 24000

_kokoro = None
_kokoro_lock = threading.Lock()          # évite double-init si deux threads simultanés
_status_proc: subprocess.Popen | None = None
_status_lock = threading.Lock()          # protège _status_proc contre race poll/terminate
_greeting_samples: np.ndarray | None = None


def _get_kokoro():
    global _kokoro
    with _kokoro_lock:
        if _kokoro is None:
            import urllib.request
            from kokoro_onnx import Kokoro
            os.makedirs(_MODELS_DIR, exist_ok=True)
            if not os.path.exists(_MODEL_PATH):
                print("Téléchargement du modèle Kokoro (~310MB)...", flush=True)
                urllib.request.urlretrieve(f"{_RELEASES_URL}/kokoro-v1.0.onnx", _MODEL_PATH)
            if not os.path.exists(_VOICES_PATH):
                print("Téléchargement des voix Kokoro...", flush=True)
                urllib.request.urlretrieve(f"{_RELEASES_URL}/voices-v1.0.bin", _VOICES_PATH)
            _kokoro = Kokoro(_MODEL_PATH, _VOICES_PATH)
    return _kokoro


def _synthesize(text: str) -> np.ndarray:
    """Retourne des samples float32 à KOKORO_SAMPLE_RATE Hz."""
    kokoro = _get_kokoro()
    t0 = time.time()
    samples, _ = kokoro.create(
        text,
        voice=KOKORO_VOICE,
        speed=KOKORO_SPEED,
        lang="fr-fr",
    )
    samples = samples.astype(np.float32)
    dt_synth = time.time() - t0
    audio_secs = len(samples) / KOKORO_SAMPLE_RATE
    n_chars = len(text)
    # Ratio durée_audio / chars — si > ~0.10s/char sur du texte court, suspect
    # (bégaiement / répétition / phonemizer qui boucle).
    ratio = audio_secs / max(n_chars, 1)
    flag = " ⚠ ratio élevé" if (ratio > 0.10 and n_chars < 40) else ""
    jlog.debug(
        "TTS",
        f"synth {audio_secs:.2f}s audio en {dt_synth:.2f}s "
        f"({n_chars}c, ratio={ratio:.3f}s/c{flag}, voice={KOKORO_VOICE}): "
        f"{jlog.trunc(text, 80)}"
    )
    return samples


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
    with _status_lock:
        if _status_proc is not None and _status_proc.poll() is None:
            _status_proc.terminate()
        _status_proc = subprocess.Popen(
            ["say", "-v", voice, text],
            stderr=subprocess.DEVNULL,
        )


def synthesize(text: str) -> np.ndarray:
    """Synthétise text → samples float32 sans jouer. Permet le pipeline overlap."""
    return _synthesize(text)


def speak(text: str, wait: bool = True) -> None:
    """Synthétise text via Kokoro et joue via sounddevice."""
    samples = _synthesize(text)
    sd.play(samples, samplerate=KOKORO_SAMPLE_RATE)
    if wait:
        sd.wait()


def cleanup() -> None:
    """Libère les ressources TTS à l'exit."""
    global _kokoro, _status_proc
    with _status_lock:
        if _status_proc is not None and _status_proc.poll() is None:
            _status_proc.terminate()
            try:
                _status_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _status_proc.kill()
    with _kokoro_lock:
        _kokoro = None


atexit.register(cleanup)
