import subprocess
from config import SAY_VOICE


def speak(text: str, voice: str = SAY_VOICE) -> None:
    subprocess.run(["say", "-v", voice, text], check=True)
