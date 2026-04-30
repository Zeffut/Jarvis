import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 0.5
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "mlx-community/whisper-turbo"

# TTS Kokoro
# Voix Kokoro disponibles (extraits) :
#   bm_george    : British male  — accent british, bégaie parfois sur le français
#   bm_lewis     : British male  — alternative british
#   am_michael   : American male — meilleur sur les phonèmes FR
#   am_adam      : American male — alternative
#   ff_siwis     : Féminine française — qualité FR optimale (perte de british)
# Override : JARVIS_KOKORO_VOICE=am_michael python3 main.py
KOKORO_VOICE = os.environ.get("JARVIS_KOKORO_VOICE", "bm_george")
KOKORO_SPEED = float(os.environ.get("JARVIS_KOKORO_SPEED", "1.0"))

# Token de fin de conversation (cf. jarvis_profile/CLAUDE.md)
END_SIGNAL = "[FIN]"

# La personnalité, les règles d'oralité et les permissions vivent désormais dans
# jarvis_profile/CLAUDE.md et jarvis_profile/.claude/settings.json.
# Le backend est Claude Code (cf. assistant.py).


def load_config(env_path: str = ".env") -> None:
    load_dotenv(env_path)
