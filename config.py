import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "mlx-community/whisper-turbo"
ELEVENLABS_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel (British, deep, butler-like)

# OpenClaw gateway
OPENCLAW_URL = "http://127.0.0.1:18789"
OPENCLAW_TOKEN = "c51f3644e24774924c3535ba36692f8c13e6bd5fd0caa062"

SYSTEM_PROMPT = (
    "Tu es Jarvis, l'assistant vocal intelligent. "
    "Tu réponds de manière concise, utile et avec une légère touche d'humour. "
    "Tu parles en français. Tes réponses doivent être courtes car elles seront lues à voix haute."
)

REQUIRED_KEYS = ["ELEVENLABS_API_KEY"]


def load_config(env_path: str = ".env") -> dict:
    load_dotenv(env_path)
    config = {}
    for key in REQUIRED_KEYS:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        config[key.lower()] = value
    return config
