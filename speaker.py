import io
import sounddevice as sd
import numpy as np
from elevenlabs import ElevenLabs
from pydub import AudioSegment

from config import ELEVENLABS_VOICE_ID


_client = None


def _get_client(api_key: str) -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=api_key)
    return _client


def speak(text: str, api_key: str, voice_id: str = ELEVENLABS_VOICE_ID) -> None:
    client = _get_client(api_key)
    audio_gen = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Collect audio bytes
    audio_bytes = b"".join(audio_gen)

    # Play with pydub + sounddevice
    audio_seg = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32) / 32768.0

    if audio_seg.channels == 2:
        samples = samples.reshape((-1, 2))

    sd.play(samples, samplerate=audio_seg.frame_rate)
    sd.wait()
