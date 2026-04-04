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
from speaker import speak
from audio import is_silent


def record_and_transcribe(transcriber: Transcriber) -> str:
    """Record audio until silence, with real-time transcription display."""
    chunks: list[np.ndarray] = []
    silence_start: float | None = None
    recording = True

    def audio_callback(indata, frames, time_info, status):
        nonlocal silence_start, recording
        chunk = indata[:, 0].copy()
        chunks.append(chunk)

        if is_silent(chunk, SILENCE_THRESHOLD):
            if silence_start is None:
                silence_start = time.time()
            elif time.time() - silence_start >= SILENCE_DURATION:
                recording = False
        else:
            silence_start = None

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=int(SAMPLE_RATE * 0.1),
        callback=audio_callback,
    ):
        # Real-time transcription display
        last_transcription_len = 0
        while recording:
            time.sleep(0.3)
            if len(chunks) > last_transcription_len + 3:
                audio_so_far = np.concatenate(chunks)
                partial = transcriber.transcribe(audio_so_far)
                if partial:
                    print(f"\r💬 {partial}", end="", flush=True)
                last_transcription_len = len(chunks)

    # Final transcription
    if not chunks:
        return ""
    full_audio = np.concatenate(chunks)
    final_text = transcriber.transcribe(full_audio)
    print(f"\r💬 {final_text}   ")
    return final_text


def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
) -> None:
    """Run a conversation: record → transcribe → ask Claude → speak → repeat until timeout."""
    while True:
        text = record_and_transcribe(transcriber)
        if not text:
            print("(rien entendu)")
            break

        print(f"\n🤖 Réflexion...")
        reply = assistant.ask(text)
        print(f"🤖 {reply}")
        speak(reply)

        # Wait for follow-up speech or timeout
        print("\n⏳ En attente...")
        silence_start = time.time()
        heard_speech = False

        def check_callback(indata, frames, time_info, status):
            nonlocal silence_start, heard_speech
            if not is_silent(indata[:, 0], SILENCE_THRESHOLD):
                heard_speech = True

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=int(SAMPLE_RATE * 0.1),
            callback=check_callback,
        ):
            while time.time() - silence_start < CONVERSATION_TIMEOUT:
                time.sleep(0.1)
                if heard_speech:
                    break

        if not heard_speech:
            break

    assistant.reset()


def main():
    print("🚀 Jarvis démarre...")
    cfg = load_config()

    print("📦 Chargement du modèle Whisper...")
    transcriber = Transcriber()

    assistant = Assistant(api_key=cfg["anthropic_api_key"])
    wake = WakeWordListener(access_key=cfg["picovoice_access_key"])

    try:
        while True:
            wake.listen()
            conversation_loop(transcriber, assistant)
    except KeyboardInterrupt:
        print("\n👋 Jarvis s'éteint.")
    finally:
        wake.cleanup()


if __name__ == "__main__":
    main()
