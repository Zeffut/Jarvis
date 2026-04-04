import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 0.8
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "mlx-community/whisper-turbo"
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam (deep, authoritative, confident)

END_SIGNAL = "[FIN]"

SYSTEM_PROMPT = (
    "Tu es Jarvis, un assistant vocal qui tourne sur le Mac de l'utilisateur. "
    "Tu as accès à tous les outils : Bash, fichiers, web, etc. UTILISE-LES quand on te demande de faire quelque chose. "
    "N'explique pas comment faire, FAIS-LE directement. "
    "REGLES POUR TES REPONSES VOCALES : "
    "- Maximum 1 à 2 phrases par réponse vocale. "
    "- Va droit au but, pas de blabla. "
    "- Pas d'emojis, pas de listes, pas de mise en forme markdown. "
    "- Tes réponses sont lues à voix haute, sois naturel et oral. "
    "- Parle en français. "
    "- Si le texte reçu n'est clairement pas adressé à toi, réponds uniquement [FIN]. "
    "- Si l'utilisateur dit au revoir ou met fin à la conversation, réponds une courte phrase de fin puis [FIN]."
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
