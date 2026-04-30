import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 0.5
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "mlx-community/whisper-turbo"

# TTS Kokoro
KOKORO_VOICE = "bm_george"  # British male — voix Jarvis
KOKORO_SPEED = 1.0

# Token de fin de conversation (cf. jarvis_profile/CLAUDE.md)
END_SIGNAL = "[FIN]"

# La personnalité, les règles d'oralité et les permissions vivent désormais dans
# jarvis_profile/CLAUDE.md et jarvis_profile/.claude/settings.json.
# Le backend est Claude Code (cf. assistant.py).


def load_config(env_path: str = ".env") -> None:
    load_dotenv(env_path)
