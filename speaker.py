from __future__ import annotations

import io
import os
import sounddevice as sd
import numpy as np
from elevenlabs import ElevenLabs
from pydub import AudioSegment

from config import ELEVENLABS_VOICE_ID


_client = None
_greeting_samples: np.ndarray | None = None
_greeting_rate: int = 22050


def _get_client(api_key: str) -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=api_key)
    return _client


def _audio_to_samples(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    audio_seg = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32) / 32768.0
    if audio_seg.channels == 2:
        samples = samples.reshape((-1, 2))
    return samples, audio_seg.frame_rate


def preload_greeting(api_key: str, voice_id: str = ELEVENLABS_VOICE_ID) -> None:
    """Pre-generate 'Oui Monsieur' at startup for instant playback."""
    global _greeting_samples, _greeting_rate

    cache_path = os.path.join(os.path.dirname(__file__), ".greeting_cache.mp3")

    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            _greeting_samples, _greeting_rate = _audio_to_samples(f.read())
        return

    client = _get_client(api_key)
    audio_gen = client.text_to_speech.convert(
        text="Oui Monsieur ?",
        voice_id=voice_id,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_22050_32",
    )
    audio_bytes = b"".join(audio_gen)

    with open(cache_path, "wb") as f:
        f.write(audio_bytes)

    _greeting_samples, _greeting_rate = _audio_to_samples(audio_bytes)


def play_greeting() -> None:
    """Play the pre-cached 'Oui Monsieur' greeting instantly."""
    if _greeting_samples is not None:
        sd.play(_greeting_samples, samplerate=_greeting_rate)
        sd.wait()


def speak(text: str, api_key: str, voice_id: str = ELEVENLABS_VOICE_ID) -> None:
    client = _get_client(api_key)
    audio_gen = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_22050_32",
    )

    audio_bytes = b"".join(audio_gen)
    samples, rate = _audio_to_samples(audio_bytes)

    sd.play(samples, samplerate=rate)
    sd.wait()
