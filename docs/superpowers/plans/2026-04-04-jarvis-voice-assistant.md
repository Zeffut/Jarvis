# Jarvis Voice Assistant — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a voice assistant that listens for "Jarvis", transcribes speech in real-time, sends to Claude Haiku 4.5, and speaks the response aloud.

**Architecture:** Wake word detection (Pvporcupine) → streaming STT (faster-whisper) → LLM (Claude Haiku 4.5) → TTS (macOS `say`). Conversation mode keeps Jarvis listening after each response for ~5s before returning to wake word detection.

**Tech Stack:** Python 3.10+, pvporcupine, sounddevice, numpy, faster-whisper, anthropic SDK, python-dotenv

---

## File Structure

```
jarvis/
├── main.py              # Point d'entrée — boucle principale (wake word → conversation → repeat)
├── config.py            # Chargement .env, constantes (seuils silence, timeouts, modèle Whisper)
├── wake_word.py         # Wrapper Pvporcupine — init, écoute, cleanup
├── audio.py             # Capture micro via sounddevice — stream audio, détection silence (RMS)
├── transcriber.py       # STT streaming via faster-whisper — transcription par chunks
├── assistant.py         # Client Claude Haiku 4.5 — prompt système, historique, appel API
├── speaker.py           # TTS via macOS `say` — exécution commande, voix Thomas
├── .env.example         # Template des clés API
├── requirements.txt     # Dépendances Python
└── tests/
    ├── test_config.py
    ├── test_audio.py
    ├── test_transcriber.py
    ├── test_assistant.py
    └── test_speaker.py
```

---

### Task 1: Project Setup — Config & Environment

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`
- Create: `.gitignore`
- Create: `tests/test_config.py`

- [ ] **Step 1: Initialize git repo and create `.gitignore`**

```bash
cd /Users/zeffut/Desktop/Projets/Jarvis
git init
```

Create `.gitignore`:

```
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.venv/
```

- [ ] **Step 2: Create `requirements.txt`**

```
pvporcupine==3.0.3
sounddevice==0.5.1
numpy==2.2.4
faster-whisper==1.1.1
anthropic==0.52.0
python-dotenv==1.1.0
pytest==8.3.5
```

- [ ] **Step 3: Create `.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
PICOVOICE_ACCESS_KEY=...
```

- [ ] **Step 4: Create virtual env and install deps**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 5: Write failing test for config**

Create `tests/test_config.py`:

```python
import os
import pytest


def test_load_config_returns_required_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-anthropic-key\nPICOVOICE_ACCESS_KEY=test-pico-key\n"
    )
    monkeypatch.chdir(tmp_path)

    from config import load_config

    cfg = load_config(env_path=str(env_file))
    assert cfg["anthropic_api_key"] == "test-anthropic-key"
    assert cfg["picovoice_access_key"] == "test-pico-key"


def test_load_config_raises_on_missing_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-key\n")
    monkeypatch.chdir(tmp_path)

    from config import load_config

    with pytest.raises(ValueError, match="PICOVOICE_ACCESS_KEY"):
        load_config(env_path=str(env_file))
```

- [ ] **Step 6: Run test to verify it fails**

```bash
python -m pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 7: Write `config.py`**

```python
import os
from dotenv import load_dotenv


# Audio constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5
CONVERSATION_TIMEOUT = 5.0
WHISPER_MODEL = "small"
CLAUDE_MODEL = "claude-haiku-4-5-20241001"
SAY_VOICE = "Thomas"

SYSTEM_PROMPT = (
    "Tu es Jarvis, l'assistant vocal intelligent. "
    "Tu réponds de manière concise, utile et avec une légère touche d'humour. "
    "Tu parles en français. Tes réponses doivent être courtes car elles seront lues à voix haute."
)

REQUIRED_KEYS = ["ANTHROPIC_API_KEY", "PICOVOICE_ACCESS_KEY"]


def load_config(env_path: str = ".env") -> dict:
    load_dotenv(env_path)
    config = {}
    for key in REQUIRED_KEYS:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        config[key.lower()] = value
    return config
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
python -m pytest tests/test_config.py -v
```

Expected: 2 passed

- [ ] **Step 9: Commit**

```bash
git add .gitignore requirements.txt .env.example config.py tests/test_config.py
git commit -m "feat: project setup with config, env, and dependencies"
```

---

### Task 2: Speaker — Text-to-Speech via macOS `say`

**Files:**
- Create: `speaker.py`
- Create: `tests/test_speaker.py`

- [ ] **Step 1: Write failing test for speaker**

Create `tests/test_speaker.py`:

```python
from unittest.mock import patch, call


def test_speak_calls_say_with_correct_args():
    from speaker import speak

    with patch("speaker.subprocess.run") as mock_run:
        speak("Bonjour monsieur")
        mock_run.assert_called_once_with(
            ["say", "-v", "Thomas", "Bonjour monsieur"],
            check=True,
        )


def test_speak_with_custom_voice():
    from speaker import speak

    with patch("speaker.subprocess.run") as mock_run:
        speak("Hello", voice="Samantha")
        mock_run.assert_called_once_with(
            ["say", "-v", "Samantha", "Hello"],
            check=True,
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_speaker.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'speaker'`

- [ ] **Step 3: Write `speaker.py`**

```python
import subprocess
from config import SAY_VOICE


def speak(text: str, voice: str = SAY_VOICE) -> None:
    subprocess.run(["say", "-v", voice, text], check=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_speaker.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add speaker.py tests/test_speaker.py
git commit -m "feat: add speaker module — TTS via macOS say"
```

---

### Task 3: Assistant — Claude Haiku 4.5 Integration

**Files:**
- Create: `assistant.py`
- Create: `tests/test_assistant.py`

- [ ] **Step 1: Write failing test for assistant**

Create `tests/test_assistant.py`:

```python
from unittest.mock import patch, MagicMock


def test_assistant_sends_message_and_returns_response():
    from assistant import Assistant

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Bonjour, comment puis-je vous aider ?")]
    mock_client.messages.create.return_value = mock_response

    with patch("assistant.anthropic.Anthropic", return_value=mock_client):
        asst = Assistant(api_key="test-key")
        reply = asst.ask("Salut Jarvis")

    assert reply == "Bonjour, comment puis-je vous aider ?"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20241001"
    assert len(call_kwargs["messages"]) == 1
    assert call_kwargs["messages"][0]["role"] == "user"
    assert call_kwargs["messages"][0]["content"] == "Salut Jarvis"


def test_assistant_maintains_conversation_history():
    from assistant import Assistant

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Réponse 1")]
    mock_client.messages.create.return_value = mock_response

    with patch("assistant.anthropic.Anthropic", return_value=mock_client):
        asst = Assistant(api_key="test-key")
        asst.ask("Question 1")
        asst.ask("Question 2")

    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]
    assert len(messages) == 3
    assert messages[0] == {"role": "user", "content": "Question 1"}
    assert messages[1] == {"role": "assistant", "content": "Réponse 1"}
    assert messages[2] == {"role": "user", "content": "Question 2"}


def test_assistant_reset_clears_history():
    from assistant import Assistant

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Réponse")]
    mock_client.messages.create.return_value = mock_response

    with patch("assistant.anthropic.Anthropic", return_value=mock_client):
        asst = Assistant(api_key="test-key")
        asst.ask("Question")
        asst.reset()
        asst.ask("Nouvelle question")

    last_call_kwargs = mock_client.messages.create.call_args[1]
    assert len(last_call_kwargs["messages"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_assistant.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'assistant'`

- [ ] **Step 3: Write `assistant.py`**

```python
import anthropic
from config import CLAUDE_MODEL, SYSTEM_PROMPT


class Assistant:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict] = []

    def ask(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )

        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        self.history.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_assistant.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add assistant.py tests/test_assistant.py
git commit -m "feat: add assistant module — Claude Haiku 4.5 integration with conversation history"
```

---

### Task 4: Audio Capture — Microphone Stream & Silence Detection

**Files:**
- Create: `audio.py`
- Create: `tests/test_audio.py`

- [ ] **Step 1: Write failing test for silence detection**

Create `tests/test_audio.py`:

```python
import numpy as np


def test_is_silent_returns_true_for_quiet_audio():
    from audio import is_silent

    quiet = np.zeros(1600, dtype=np.float32)
    assert is_silent(quiet, threshold=0.01) is True


def test_is_silent_returns_false_for_loud_audio():
    from audio import is_silent

    loud = np.ones(1600, dtype=np.float32) * 0.5
    assert is_silent(loud, threshold=0.01) is False


def test_is_silent_at_boundary():
    from audio import is_silent

    boundary = np.ones(1600, dtype=np.float32) * 0.01
    assert is_silent(boundary, threshold=0.01) is False

    just_below = np.ones(1600, dtype=np.float32) * 0.009
    assert is_silent(just_below, threshold=0.01) is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_audio.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'audio'`

- [ ] **Step 3: Write `audio.py`**

```python
import numpy as np
import sounddevice as sd
from config import SAMPLE_RATE


def is_silent(audio_chunk: np.ndarray, threshold: float) -> bool:
    rms = np.sqrt(np.mean(audio_chunk**2))
    return rms < threshold


def create_audio_stream(callback, sample_rate: int = SAMPLE_RATE) -> sd.InputStream:
    return sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=int(sample_rate * 0.1),  # 100ms chunks
        callback=callback,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_audio.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add audio.py tests/test_audio.py
git commit -m "feat: add audio module — mic stream and silence detection"
```

---

### Task 5: Transcriber — Streaming STT via faster-whisper

**Files:**
- Create: `transcriber.py`
- Create: `tests/test_transcriber.py`

- [ ] **Step 1: Write failing test for transcriber**

Create `tests/test_transcriber.py`:

```python
from unittest.mock import patch, MagicMock
import numpy as np


def test_transcriber_init_loads_model():
    from transcriber import Transcriber

    with patch("transcriber.WhisperModel") as mock_model_cls:
        t = Transcriber(model_size="small")
        mock_model_cls.assert_called_once_with("small", compute_type="auto")


def test_transcribe_returns_text():
    from transcriber import Transcriber

    mock_segment = MagicMock()
    mock_segment.text = " Bonjour Jarvis"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], None)

    with patch("transcriber.WhisperModel", return_value=mock_model):
        t = Transcriber(model_size="small")
        result = t.transcribe(np.zeros(16000, dtype=np.float32))

    assert result == "Bonjour Jarvis"


def test_transcribe_empty_audio_returns_empty_string():
    from transcriber import Transcriber

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([], None)

    with patch("transcriber.WhisperModel", return_value=mock_model):
        t = Transcriber(model_size="small")
        result = t.transcribe(np.zeros(16000, dtype=np.float32))

    assert result == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_transcriber.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'transcriber'`

- [ ] **Step 3: Write `transcriber.py`**

```python
import numpy as np
from faster_whisper import WhisperModel
from config import WHISPER_MODEL


class Transcriber:
    def __init__(self, model_size: str = WHISPER_MODEL):
        self.model = WhisperModel(model_size, compute_type="auto")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(audio, language="fr")
        text = "".join(seg.text for seg in segments).strip()
        return text
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_transcriber.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add transcriber.py tests/test_transcriber.py
git commit -m "feat: add transcriber module — streaming STT via faster-whisper"
```

---

### Task 6: Wake Word — Pvporcupine Integration

**Files:**
- Create: `wake_word.py`
- Create: `tests/test_wake_word.py`

- [ ] **Step 1: Write failing test for wake word**

Create `tests/test_wake_word.py`:

```python
from unittest.mock import patch, MagicMock


def test_wake_word_listener_init():
    from wake_word import WakeWordListener

    mock_porcupine = MagicMock()
    mock_porcupine.frame_length = 512
    mock_porcupine.sample_rate = 16000

    with patch("wake_word.pvporcupine.create", return_value=mock_porcupine) as mock_create:
        listener = WakeWordListener(access_key="test-key")
        mock_create.assert_called_once_with(
            access_key="test-key",
            keywords=["jarvis"],
        )
        assert listener.porcupine == mock_porcupine


def test_wake_word_listener_cleanup():
    from wake_word import WakeWordListener

    mock_porcupine = MagicMock()
    mock_porcupine.frame_length = 512
    mock_porcupine.sample_rate = 16000

    with patch("wake_word.pvporcupine.create", return_value=mock_porcupine):
        listener = WakeWordListener(access_key="test-key")
        listener.cleanup()
        mock_porcupine.delete.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_wake_word.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'wake_word'`

- [ ] **Step 3: Write `wake_word.py`**

```python
import numpy as np
import pvporcupine
import sounddevice as sd


class WakeWordListener:
    def __init__(self, access_key: str):
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["jarvis"],
        )
        self.frame_length = self.porcupine.frame_length
        self.sample_rate = self.porcupine.sample_rate

    def listen(self) -> None:
        """Block until 'Jarvis' is detected."""
        print("\n🟢 En écoute...")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_length,
        ) as stream:
            while True:
                audio_frame, _ = stream.read(self.frame_length)
                pcm = audio_frame.flatten()
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    print("🎙️  Je vous écoute...")
                    return

    def cleanup(self) -> None:
        self.porcupine.delete()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_wake_word.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add wake_word.py tests/test_wake_word.py
git commit -m "feat: add wake word module — Pvporcupine Jarvis detection"
```

---

### Task 7: Main Loop — Assemble Everything

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write `main.py`**

```python
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
```

- [ ] **Step 2: Smoke test — run Jarvis**

```bash
source .venv/bin/activate
python main.py
```

Expected: Jarvis starts, loads Whisper model, shows "🟢 En écoute...". Say "Jarvis" to test the full flow. Ctrl+C to stop.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main loop — complete Jarvis voice assistant"
```

---

### Task 8: End-to-End Manual Test & Polish

- [ ] **Step 1: Create `.env` with real keys**

```bash
cp .env.example .env
# Edit .env with your real ANTHROPIC_API_KEY and PICOVOICE_ACCESS_KEY
```

- [ ] **Step 2: Download Whisper model (first run)**

The first run of `faster-whisper` will download the `small` model automatically. This takes ~1 minute.

- [ ] **Step 3: Full end-to-end test**

```bash
python main.py
```

Test checklist:
- "Jarvis" wake word triggers detection
- Speech is transcribed in real-time (words appear as you speak)
- Claude responds with a relevant answer
- Response is spoken aloud by macOS `say`
- Conversation mode: follow-up question works without saying "Jarvis" again
- After ~5s of silence, Jarvis returns to wake word mode
- Ctrl+C exits cleanly

- [ ] **Step 4: Adjust thresholds if needed**

If silence detection is too sensitive or not sensitive enough, adjust in `config.py`:
- `SILENCE_THRESHOLD`: raise if Jarvis cuts you off too early, lower if it waits too long
- `SILENCE_DURATION`: raise for longer pauses between words
- `CONVERSATION_TIMEOUT`: raise to keep conversation mode longer

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Jarvis v1 complete — wake word, streaming STT, Claude, TTS"
```
