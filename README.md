# Jarvis

A voice-controlled AI assistant for macOS, powered by Claude Code. Say "Jarvis" and it listens, transcribes, thinks, and speaks back — with an optional native macOS "Vibe Island" UI.

## Features

- **Wake word detection** - Say "Jarvis" to activate (faster-whisper tiny, rolling buffer)
- **Real-time transcription** - See your words appear as you speak (faster-whisper tiny preview + mlx-whisper turbo final)
- **Claude Code backend** - Full access to tools: Bash, file system, web search, code editing (persistent `claude` subprocess)
- **Natural voice, 100% local** - Kokoro ONNX text-to-speech (no API key, runs offline on Apple Silicon)
- **Streaming responses** - Text appears token by token, TTS plays sentence by sentence on a background thread
- **Conversation mode** - Follow-up questions without repeating "Jarvis"
- **Auto-end detection** - Jarvis stops listening on silence timeout, the `[FIN]` marker, or when you're talking to someone else
- **Native UI (optional)** - "Vibe Island" Dynamic-Island-style panel built in SwiftUI/AppKit, with a 3D Fibonacci orb that reacts to state. Communicates with the Python backend over Unix sockets. Enabled via `JARVIS_UI=1` (off by default).

## Architecture

```
Mic --> Wake word (faster-whisper tiny, rolling buffer)
    --> Record + live preview (faster-whisper tiny)
    --> Final transcription (mlx-whisper turbo on Apple Silicon GPU)
    --> Claude Code CLI (persistent process, stream-json, isolated jarvis_profile/)
    --> Kokoro ONNX TTS (local, sentence by sentence, background thread, 24 kHz)
    --> Speaker (mic muted while speaking)
    --> Conversation mode (mic stays open) or back to wake word

Optional native UI (JARVIS_UI=1):
  Python  --(/tmp/jarvis-ui.sock, JSON: state/amplitude/tool_name/question)-->  Swift VibeIsland
  Swift   --(/tmp/jarvis-ui-events.sock, JSON: choice)-->                        Python
```

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.9+
- [Claude Code](https://claude.com/claude-code) CLI installed and authenticated
- Swift toolchain (Xcode / Command Line Tools) — only if you want the native Vibe Island UI
- No TTS API key required: the voice runs fully locally via Kokoro. The Kokoro model weights (~310 MB ONNX + voices) are downloaded automatically on first run from the [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) GitHub releases into `models/`.

## Setup

```bash
git clone https://github.com/TDS-Upec/Jarvis.git
cd Jarvis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No `.env` is required to run Jarvis. All TTS is local (no API key). Optional environment variables are documented in **Configuration** below and in `.env.example`.

### Claude Code profile (isolated)

The Claude Code backend runs against an **isolated profile** in `jarvis_profile/`, using its own config home (`jarvis_profile/.claude_home/`, set via `CLAUDE_CONFIG_DIR`). This keeps Jarvis independent of your global Claude Code hooks/plugins/MCP and gives a fast, deterministic startup. Authenticate that profile once:

```bash
cd jarvis_profile && ./login.sh   # exports CLAUDE_CONFIG_DIR=.claude_home, then runs: claude /login
```

The `jarvis_profile/.claude_home/` directory holds OAuth credentials and is git-ignored (never committed).

## Usage

### Quick start (with the native UI)

```bash
./start.sh
```

`start.sh` builds the Swift UI if needed (`swift build -c release` in `ui/`), launches the Vibe Island binary in the background with `JARVIS_UI=1`, then runs `main.py` in the foreground. Ctrl+C stops both cleanly. It expects the venv at `.venv/bin/python3`.

### Headless (terminal only, no Swift UI)

```bash
source .venv/bin/activate
python main.py
```

Say **"Jarvis"** to activate, then speak naturally in French.

### Building the native UI manually

```bash
cd ui
swift build -c release      # produces ui/.build/release/JarvisUI
```

## Project Structure

```
main.py            - Main loop, mic buffer, conversation state machine, TTS pipeline
assistant.py       - Claude Code CLI integration (persistent stream-json subprocess), AskUserQuestion bridge
transcriber.py     - Final speech-to-text via mlx-whisper (Apple Silicon GPU)
wake_word.py       - Wake word "Jarvis" detection via faster-whisper tiny (rolling buffer)
speaker.py         - Text-to-speech via Kokoro ONNX (local); greeting cache
audio.py           - Audio helpers (RMS silence detection)
config.py          - Audio constants and Kokoro TTS settings
ui.py              - Terminal UI (styled ANSI output)
ui_socket.py       - IPC bridge to the Swift UI (Unix sockets, fire-and-forget; gated by JARVIS_UI)
jlog.py            - Custom logger (file + stdout, per-component colors)
start.sh           - Launcher: build + run Swift UI and main.py together
requirements.txt   - Pinned Python dependencies
jarvis_profile/    - Isolated Claude Code profile (CLAUDE.md persona, settings, .claude_home auth)
ui/                - Native macOS Swift app (SwiftPM "JarvisUI", Vibe Island)
  Package.swift
  Sources/JarvisUI/
    main.swift, AppDelegate.swift
    IPC/            - SocketListener.swift (Python->Swift), EventSender.swift (Swift->Python)
    VibeIsland/     - VibeIslandPanel/View, OrbView (Fibonacci orb), QuestionPanelView, etc.
scripts/           - Manual dev tools (test_vibe.py, test_event_roundtrip.py) — NOT pytest tests
tests/             - pytest suite (audio, config, speaker, transcriber, wake_word, sockets, assistant)
```

## Configuration

All configuration is via environment variables (no `.env` required):

| Variable | Default | Effect |
| --- | --- | --- |
| `JARVIS_UI` | `0` | `1` enables the native Swift Vibe Island UI and all socket sends |
| `JARVIS_MODEL` | `claude-haiku-4-5` | Claude Code model used by the backend |
| `JARVIS_KOKORO_VOICE` | `ff_siwis` | Kokoro TTS voice (e.g. `am_michael`, `bm_george`) |
| `JARVIS_KOKORO_SPEED` | `1.0` | Kokoro TTS speed multiplier |
| `JARVIS_LOG` | `/tmp/jarvis.log` | Log file path |
| `JARVIS_NO_COLOR` | unset | `1` disables ANSI colors in logs |

Audio thresholds and timings live in `config.py` (`SILENCE_DURATION` = 0.5s, `CONVERSATION_TIMEOUT` = 5.0s, `SAMPLE_RATE` = 16000, `WHISPER_MODEL` = `mlx-community/whisper-turbo`). The assistant's personality and tool permissions live in `jarvis_profile/CLAUDE.md` and `jarvis_profile/.claude/settings.json`.

## Testing

```bash
source .venv/bin/activate
pytest tests/
```

`scripts/test_vibe.py` and `scripts/test_event_roundtrip.py` are **manual** dev tools to exercise the UI sockets live — despite the `test_` prefix they are not pytest tests, so don't point pytest at `scripts/`.

## Built With

- [Claude Code](https://claude.com/claude-code) - AI backend with full tool access
- [mlx-whisper](https://github.com/ml-explore/mlx-examples) - Speech-to-text optimized for Apple Silicon
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Lightweight STT for wake word + live preview
- [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) - Local, offline neural text-to-speech
- [sounddevice](https://python-sounddevice.readthedocs.io) - Audio capture and playback
- SwiftUI / AppKit - Native macOS "Vibe Island" UI
