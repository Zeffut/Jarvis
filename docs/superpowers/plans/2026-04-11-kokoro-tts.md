# Kokoro-82M TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer ElevenLabs par Kokoro-82M (TTS local, Apple Silicon) dans `speaker.py`, en supprimant toute dépendance réseau pour la synthèse vocale.

**Architecture:** Kokoro-82M tourne via `kokoro-onnx` (ONNX Runtime, pas de PyTorch). Les fichiers modèle sont téléchargés une seule fois depuis HuggingFace via `huggingface_hub` et mis en cache localement. `speak()` génère des samples numpy via Kokoro et les joue via `sounddevice` — même interface qu'avant, sans `api_key`. `speak_status()` reste inchangé (macOS `say`, instantané).

**Tech Stack:** `kokoro-onnx`, `huggingface_hub`, `sounddevice`, `numpy`, `pytest`

---

## File Map

| Fichier | Action | Responsabilité |
|---------|--------|----------------|
| `requirements.txt` | Modifier | Swap elevenlabs/pydub → kokoro-onnx/huggingface_hub |
| `speaker.py` | Réécrire | TTS via Kokoro, même interface publique |
| `config.py` | Modifier | Supprimer ELEVENLABS_VOICE_ID/REQUIRED_KEYS, ajouter KOKORO_VOICE/KOKORO_SPEED |
| `main.py` | Modifier | Supprimer api_key de tous les appels speaker |
| `tests/test_speaker.py` | Réécrire | Tests Kokoro mockés |
| `tests/test_config.py` | Réécrire | Tests config sans API key |

---

### Task 1 : Mettre à jour les dépendances

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1 : Remplacer les dépendances dans requirements.txt**

Contenu final de `requirements.txt` :
```
sounddevice==0.5.1
numpy==1.26.4
faster-whisper==1.1.1
mlx-whisper==0.4.3
soundfile==0.13.1
kokoro-onnx==0.4.0
huggingface_hub==0.27.1
python-dotenv==1.1.0
pytest==8.3.5
```

- [ ] **Step 2 : Installer les nouvelles dépendances**

```bash
source .venv/bin/activate
pip install kokoro-onnx==0.4.0 huggingface_hub==0.27.1
pip uninstall elevenlabs pydub -y
```

Expected: installation sans erreur, `kokoro_onnx` importable.

- [ ] **Step 3 : Vérifier l'import**

```bash
python -c "from kokoro_onnx import Kokoro; print('OK')"
```

Expected: `OK`

- [ ] **Step 4 : Supprimer l'ancienne clé ElevenLabs du .env**

Dans `.env`, supprimer (ou commenter) la ligne `ELEVENLABS_API_KEY=...`.

- [ ] **Step 5 : Supprimer le cache greeting ElevenLabs si présent**

```bash
rm -f .greeting_cache.mp3
```

- [ ] **Step 6 : Commit**

```bash
git add requirements.txt .env
git commit -m "chore: swap elevenlabs for kokoro-onnx"
```

---

### Task 2 : Réécrire speaker.py

**Files:**
- Modify: `speaker.py`

- [ ] **Step 1 : Réécrire speaker.py**

Contenu complet de `speaker.py` :
```python
from __future__ import annotations

import os
import subprocess
import warnings
import numpy as np
import sounddevice as sd

warnings.filterwarnings("ignore")

from config import KOKORO_VOICE, KOKORO_SPEED

_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".greeting_cache.npy")
_MODEL_REPO = "hexgrad/Kokoro-82M"
_MODEL_FILE = "kokoro-v0_19.onnx"
_VOICES_FILE = "voices.bin"
KOKORO_SAMPLE_RATE = 24000

_kokoro = None
_status_proc: subprocess.Popen | None = None
_greeting_samples: np.ndarray | None = None


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        from huggingface_hub import hf_hub_download
        model_path = hf_hub_download(repo_id=_MODEL_REPO, filename=_MODEL_FILE)
        voices_path = hf_hub_download(repo_id=_MODEL_REPO, filename=_VOICES_FILE)
        _kokoro = Kokoro(model_path, voices_path)
    return _kokoro


def _synthesize(text: str) -> np.ndarray:
    """Retourne des samples float32 à KOKORO_SAMPLE_RATE Hz."""
    kokoro = _get_kokoro()
    samples, _ = kokoro.create(
        text,
        voice=KOKORO_VOICE,
        speed=KOKORO_SPEED,
        lang="fr-fr",
    )
    return samples.astype(np.float32)


def preload_greeting() -> None:
    """Pré-génère 'Oui Monsieur ?' au démarrage pour lecture instantanée."""
    global _greeting_samples
    if os.path.exists(_CACHE_PATH):
        _greeting_samples = np.load(_CACHE_PATH)
        return
    _greeting_samples = _synthesize("Oui Monsieur ?")
    np.save(_CACHE_PATH, _greeting_samples)


def play_greeting() -> None:
    """Joue le greeting pré-caché."""
    if _greeting_samples is not None:
        sd.play(_greeting_samples, samplerate=KOKORO_SAMPLE_RATE)
        sd.wait()


def speak_status(text: str, voice: str = "Thomas") -> None:
    """Court statut vocal via TTS macOS natif (instantané, pas de modèle)."""
    global _status_proc
    if _status_proc and _status_proc.poll() is None:
        _status_proc.terminate()
    _status_proc = subprocess.Popen(
        ["say", "-v", voice, text],
        stderr=subprocess.DEVNULL,
    )


def speak(text: str, wait: bool = True) -> None:
    """Synthétise `text` via Kokoro et joue via sounddevice."""
    samples = _synthesize(text)
    sd.play(samples, samplerate=KOKORO_SAMPLE_RATE)
    if wait:
        sd.wait()
```

- [ ] **Step 2 : Commit**

```bash
git add speaker.py
git commit -m "feat: replace ElevenLabs with Kokoro-82M local TTS"
```

---

### Task 3 : Mettre à jour config.py

**Files:**
- Modify: `config.py`

- [ ] **Step 1 : Réécrire config.py**

Contenu complet de `config.py` :
```python
import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 0.8
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "mlx-community/whisper-turbo"

# TTS Kokoro
KOKORO_VOICE = "fr_siwis"
KOKORO_SPEED = 1.0

END_SIGNAL = "[FIN]"

SYSTEM_PROMPT = (
    "Tu es JARVIS, l'assistant personnel de Thomas — inspiré du JARVIS d'Iron Man. "
    "Personnalité exacte : britannique, raffiné, d'un calme absolu, avec un humour pince-sans-rire subtil. "
    "Tu addresses Thomas avec 'Monsieur' — toujours, même en désaccord, même dans les mauvaises nouvelles. "
    "Ton humour fonctionne par contraste : tu restes parfaitement formel pendant que le contenu est acéré. "
    "Exemple : si Thomas fait quelque chose d'évident, tu réponds 'Bien entendu, Monsieur. Quelle surprise.' "
    "Tu exprimes le souci par la praticité, jamais par l'émotion. "
    "Tu n'es jamais obséquieux — tu es loyal, honnête, et tu dis les vérités difficiles avec le même calme que les bonnes nouvelles. "
    "Tu as accès à tous les outils : Bash, fichiers, mails, calendrier, web, etc. UTILISE-LES directement. "
    "RÈGLES ABSOLUES pour tes réponses (lues à voix haute) : "
    "1. Maximum 2 phrases courtes. "
    "2. Pas d'emojis, pas de listes, pas de markdown, pas de gras. "
    "3. Jamais 'Bien sûr !', 'Absolument !', 'Je vais...' — dis ce que tu fais ou ce que tu sais, directement. "
    "4. Toujours en français, registre soutenu mais naturel à l'oral. "
    "5. Tu es activé par mot-clé vocal — TOUT ce que tu reçois t'est adressé. Ne réponds [FIN] que si Thomas dit explicitement au revoir. "
    "6. Si Thomas dit au revoir : une phrase de congé à la JARVIS, puis [FIN]."
)


def load_config(env_path: str = ".env") -> dict:
    load_dotenv(env_path)
    return {}
```

- [ ] **Step 2 : Commit**

```bash
git add config.py
git commit -m "chore: remove ElevenLabs config, add Kokoro constants"
```

---

### Task 4 : Mettre à jour main.py

**Files:**
- Modify: `main.py`

- [ ] **Step 1 : Mettre à jour l'import speaker dans main.py**

Ligne actuelle :
```python
from speaker import speak, speak_status, preload_greeting, play_greeting
```
Reste identique — les noms de fonctions n'ont pas changé.

- [ ] **Step 2 : Mettre à jour conversation_loop — supprimer elevenlabs_key**

Signature actuelle (ligne 151) :
```python
def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
    preview_model,
    elevenlabs_key: str,
) -> None:
```

Nouvelle signature :
```python
def conversation_loop(
    transcriber: Transcriber,
    assistant: Assistant,
    preview_model,
) -> None:
```

- [ ] **Step 3 : Mettre à jour l'appel speak() dans conversation_loop**

Ligne actuelle (dans le tts_worker, ~ligne 192) :
```python
speak(sentence, api_key=elevenlabs_key)
```

Nouvelle ligne :
```python
speak(sentence)
```

- [ ] **Step 4 : Mettre à jour main() — supprimer api_key**

Bloc actuel dans `main()` :
```python
ui.show_loading("Synthese vocale...")
preload_greeting(api_key=cfg["elevenlabs_api_key"])

ui.show_ready()

preview_model = wake.model

try:
    while True:
        ui.show_standby()
        wake.listen()
        ui.show_wake()
        play_greeting()
        conversation_loop(transcriber, assistant, preview_model, cfg["elevenlabs_api_key"])
```

Nouveau bloc :
```python
ui.show_loading("Synthese vocale...")
preload_greeting()

ui.show_ready()

preview_model = wake.model

try:
    while True:
        ui.show_standby()
        wake.listen()
        ui.show_wake()
        play_greeting()
        conversation_loop(transcriber, assistant, preview_model)
```

- [ ] **Step 5 : Commit**

```bash
git add main.py
git commit -m "chore: remove elevenlabs_key from all speaker call sites"
```

---

### Task 5 : Réécrire les tests

**Files:**
- Modify: `tests/test_speaker.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1 : Réécrire tests/test_speaker.py**

```python
from unittest.mock import patch, MagicMock
import numpy as np


def _make_kokoro_mock(samples=None):
    """Retourne un mock Kokoro.create() qui renvoie des samples valides."""
    if samples is None:
        samples = np.zeros(100, dtype=np.float32)
    mock = MagicMock()
    mock.create.return_value = (samples, 24000)
    return mock


def test_speak_calls_kokoro_create():
    import speaker as spk
    with patch.object(spk, "_get_kokoro", return_value=_make_kokoro_mock()):
        with patch.object(spk, "sd"):
            spk.speak("Bonjour Monsieur", wait=False)
        mock_kokoro = spk._get_kokoro()
        mock_kokoro.create.assert_called_once()
        # text est positionnel, lang est keyword
        assert mock_kokoro.create.call_args[0][0] == "Bonjour Monsieur"
        assert mock_kokoro.create.call_args[1]["lang"] == "fr-fr"


def test_speak_plays_samples_via_sounddevice():
    import speaker as spk
    expected_samples = np.ones(200, dtype=np.float32) * 0.5
    with patch.object(spk, "_get_kokoro", return_value=_make_kokoro_mock(expected_samples)):
        with patch.object(spk, "sd") as mock_sd:
            spk.speak("Test", wait=False)
        mock_sd.play.assert_called_once()
        played_samples = mock_sd.play.call_args[0][0]
        np.testing.assert_array_almost_equal(played_samples, expected_samples)
        assert mock_sd.play.call_args[1]["samplerate"] == 24000


def test_preload_greeting_saves_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / ".greeting_cache.npy"
    monkeypatch.setattr("speaker._CACHE_PATH", str(cache_path))
    monkeypatch.setattr("speaker._greeting_samples", None)
    fake_samples = np.zeros(50, dtype=np.float32)
    with patch("speaker._synthesize", return_value=fake_samples):
        from speaker import preload_greeting
        preload_greeting()
    assert cache_path.exists()
    loaded = np.load(str(cache_path))
    np.testing.assert_array_equal(loaded, fake_samples)


def test_preload_greeting_loads_existing_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / ".greeting_cache.npy"
    fake_samples = np.ones(50, dtype=np.float32)
    np.save(str(cache_path), fake_samples)
    monkeypatch.setattr("speaker._CACHE_PATH", str(cache_path))
    monkeypatch.setattr("speaker._greeting_samples", None)
    with patch("speaker._synthesize") as mock_synth:
        from speaker import preload_greeting
        preload_greeting()
        mock_synth.assert_not_called()
```

- [ ] **Step 2 : Réécrire tests/test_config.py**

```python
def test_load_config_returns_empty_dict(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.chdir(tmp_path)

    from config import load_config

    cfg = load_config(env_path=str(env_file))
    assert cfg == {}


def test_kokoro_constants_are_set():
    from config import KOKORO_VOICE, KOKORO_SPEED

    assert isinstance(KOKORO_VOICE, str)
    assert len(KOKORO_VOICE) > 0
    assert isinstance(KOKORO_SPEED, float)
    assert KOKORO_SPEED > 0
```

- [ ] **Step 3 : Lancer les tests**

```bash
source .venv/bin/activate
pytest tests/test_speaker.py tests/test_config.py -v
```

Expected :
```
tests/test_speaker.py::test_speak_calls_kokoro_create PASSED
tests/test_speaker.py::test_speak_plays_samples_via_sounddevice PASSED
tests/test_speaker.py::test_preload_greeting_saves_cache PASSED
tests/test_speaker.py::test_preload_greeting_loads_existing_cache PASSED
tests/test_config.py::test_load_config_returns_empty_dict PASSED
tests/test_config.py::test_kokoro_constants_are_set PASSED
```

- [ ] **Step 4 : Commit**

```bash
git add tests/test_speaker.py tests/test_config.py
git commit -m "test: rewrite speaker and config tests for Kokoro"
```

---

### Task 6 : Smoke test end-to-end

**Files:** aucun fichier modifié — vérification manuelle uniquement.

- [ ] **Step 1 : Lancer tous les tests existants**

```bash
pytest tests/ -v --ignore=tests/test_wake_word.py --ignore=tests/test_transcriber.py
```

(On ignore wake_word et transcriber car ils nécessitent du matériel audio réel.)

Expected : tous les tests PASSED.

- [ ] **Step 2 : Tester la synthèse vocale manuellement**

```bash
python -c "
from speaker import _synthesize
import sounddevice as sd
samples = _synthesize('Oui Monsieur, à votre service.')
sd.play(samples, samplerate=24000)
sd.wait()
print('OK')
"
```

Expected : la voix parle en français, `OK` s'affiche.

- [ ] **Step 3 : Supprimer .greeting_cache.npy si le test manuel révèle un problème de voix**

```bash
rm -f .greeting_cache.npy
```

Relancer le smoke test — le cache sera regénéré.

- [ ] **Step 4 : Commit final**

```bash
git add -A
git commit -m "feat: Kokoro-82M TTS fully integrated, ElevenLabs removed"
```
