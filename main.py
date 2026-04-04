from __future__ import annotations

import sys
import time
import numpy as np
import sounddevice as sd

from config import (
    load_config,
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    CONVERSATION_TIMEOUT,
)
from wake_word import WakeWordListener
from transcriber import Transcriber
from assistant import Assistant
from speaker import speak, preload_greeting, play_greeting
from audio import is_silent


def record_and_transcribe(transcriber: Transcriber, timeout: float = 0) -> str:
    """Record audio until silence, then transcribe. Waits for speech first.

    If timeout > 0, returns empty string if no speech detected within timeout seconds.
    """
    chunks: list[np.ndarray] = []
    silence_start: float | None = None
    speech_started = False
    recording = True
    timed_out = False

    def audio_callback(indata, frames, time_info, status):
        nonlocal silence_start, recording, speech_started
        chunk = indata[:, 0].copy()

        if not speech_started:
            if not is_silent(chunk, SILENCE_THRESHOLD):
                speech_started = True
                chunks.append(chunk)
            return

        chunks.append(chunk)

        if is_silent(chunk, SILENCE_THRESHOLD):
            if silence_start is None:
                silence_start = time.time()
            elif time.time() - silence_start >= SILENCE_DURATION:
                recording = False
        else:
            silence_start = None

    print("🎤 ...", end="", flush=True)
    start_time = time.time()
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=int(SAMPLE_RATE * 0.1),
        callback=audio_callback,
    ):
        while recording:
            time.sleep(0.05)
            if timeout > 0 and not speech_started and time.time() - start_time >= timeout:
                timed_out = True
                break

    if timed_out or not chunks:
        print("\r   ", end="\r")
        return ""

    if not chunks:
        return ""

    full_audio = np.concatenate(chunks)
    final_text = transcriber.transcribe(full_audio)
    print(f"\r💬 {final_text}   ")
    return final_text


def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
    elevenlabs_key: str,
) -> None:
    """Run a conversation: record → transcribe → ask Claude (stream) → speak per sentence."""
    first_turn = True
    while True:
        # First turn: no timeout (user just said "Jarvis")
        # Follow-up turns: timeout after CONVERSATION_TIMEOUT seconds of no speech
        timeout = 0 if first_turn else CONVERSATION_TIMEOUT
        text = record_and_transcribe(transcriber, timeout=timeout)
        first_turn = False

        if not text:
            break

        print(f"\n🤖 ", end="", flush=True)

        # Stream Claude response and speak sentence by sentence
        for sentence in assistant.ask_stream(text):
            print(sentence, end=" ", flush=True)
            speak(sentence, api_key=elevenlabs_key)

        print()

    assistant.reset()


def main():
    print("🚀 Jarvis démarre...")
    cfg = load_config()

    print("📦 Chargement du modèle Whisper...")
    transcriber = Transcriber()

    assistant = Assistant(api_key=cfg["anthropic_api_key"])

    print("📦 Chargement du modèle wake word...")
    wake = WakeWordListener()

    print("🔊 Pré-chargement de la voix...")
    preload_greeting(api_key=cfg["elevenlabs_api_key"])

    try:
        while True:
            wake.listen()
            play_greeting()
            conversation_loop(transcriber, assistant, cfg["elevenlabs_api_key"])
    except KeyboardInterrupt:
        print("\n👋 Jarvis s'éteint.")
    finally:
        wake.cleanup()


if __name__ == "__main__":
    main()
