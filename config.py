import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "turbo"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
ELEVENLABS_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel (British, deep, butler-like)

SYSTEM_PROMPT = (
    "Tu es Jarvis, l'assistant vocal intelligent. "
    "Tu réponds de manière concise, utile et avec une légère touche d'humour. "
    "Tu parles en français. Tes réponses doivent être courtes car elles seront lues à voix haute."
)

REQUIRED_KEYS = ["ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY"]


def load_config(env_path: str = ".env") -> dict:
    load_dotenv(env_path)
    config = {}
    for key in REQUIRED_KEYS:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        config[key.lower()] = value
    return config
