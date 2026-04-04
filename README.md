# Jarvis

A voice-controlled AI assistant for macOS, powered by Claude Code. Say "Jarvis" and it listens, transcribes, thinks, and speaks back.

## Features

- **Wake word detection** - Say "Jarvis" to activate (faster-whisper tiny, rolling buffer)
- **Real-time transcription** - See your words appear as you speak (faster-whisper preview + mlx-whisper turbo final)
- **Claude Code backend** - Full access to tools: Bash, file system, web search, code editing
- **Natural voice** - ElevenLabs multilingual v2 text-to-speech
- **Streaming responses** - Text appears token by token, TTS plays sentence by sentence
- **Conversation mode** - Follow-up questions without repeating "Jarvis"
- **Auto-end detection** - Jarvis stops listening when you're done or talking to someone else

## Architecture

```
Mic --> Wake word (faster-whisper tiny, rolling buffer)
    --> Record + live preview (faster-whisper tiny)
    --> Final transcription (mlx-whisper turbo on Apple Silicon GPU)
    --> Claude Code CLI (persistent process, stream-json)
    --> ElevenLabs TTS (sentence by sentence, background thread)
    --> Speaker
    --> Conversation mode (mic stays open) or back to wake word
```

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.9+
- [Claude Code](https://claude.ai/claude-code) installed and authenticated
- [ElevenLabs](https://elevenlabs.io) API key (free tier: 10,000 chars/month)
- ffmpeg (`brew install ffmpeg`)

## Setup

```bash
git clone https://github.com/TDS-Upec/Jarvis.git
cd Jarvis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your ElevenLabs API key
```

## Usage

```bash
source .venv/bin/activate
python main.py
```

Say **"Jarvis"** to activate, then speak naturally in French.

## Project Structure

```
main.py          - Main loop, mic buffer, conversation flow
assistant.py     - Claude Code CLI integration (persistent process)
transcriber.py   - Speech-to-text via mlx-whisper (Apple Silicon GPU)
wake_word.py     - Wake word detection via faster-whisper (rolling buffer)
speaker.py       - Text-to-speech via ElevenLabs
audio.py         - Audio capture and silence detection
config.py        - Configuration and constants
ui.py            - Terminal UI (styled output)
```

## Configuration

Edit `config.py` to adjust:
- `SILENCE_DURATION` - How long to wait before cutting (default: 0.8s)
- `CONVERSATION_TIMEOUT` - Silence before ending conversation (default: 5s)
- `ELEVENLABS_VOICE_ID` - Change the voice
- `WHISPER_MODEL` - Change the transcription model

## Built With

- [Claude Code](https://claude.ai/claude-code) - AI backend with full tool access
- [mlx-whisper](https://github.com/ml-explore/mlx-examples) - Speech-to-text optimized for Apple Silicon
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Lightweight STT for wake word
- [ElevenLabs](https://elevenlabs.io) - Natural text-to-speech
- [sounddevice](https://python-sounddevice.readthedocs.io) - Audio capture
