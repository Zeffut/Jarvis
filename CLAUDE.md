# CLAUDE.md — Jarvis

Assistant vocal macOS (Apple Silicon). Backend = Claude Code CLI. TTS = Kokoro ONNX **local** (jamais ElevenLabs — toute mention d'ElevenLabs dans la doc historique est obsolète).

## Pipeline (qui appelle quoi)

`main.py` (boucle + machine à états) → `wake_word.py` (faster-whisper tiny, wake "Jarvis") → `transcriber.py` (mlx-whisper turbo, GPU MLX) → `assistant.py` (subprocess `claude` persistant, stream-json bidirectionnel) → `speaker.py` (Kokoro ONNX, voix `ff_siwis`, 24 kHz, joue phrase par phrase). `ui.py` = UI terminal. `ui_socket.py` = pont sockets vers l'UI Swift. `jlog.py` = logger. `config.py` = constantes audio + Kokoro (`WHISPER_MODEL` y vit et est importé par `transcriber.py`).

## Commandes

- Lancer (UI Swift + Python) : `./start.sh` (build l'UI si absente, lance JarvisUI en background avec `JARVIS_UI=1`, puis `main.py`). Attend le venv en `.venv/bin/python3`.
- Lancer headless (terminal seul) : `source .venv/bin/activate && python main.py`.
- Tester : `source .venv/bin/activate && pytest tests/`. NE PAS lancer pytest sur `scripts/` (`test_vibe.py` / `test_event_roundtrip.py` sont des outils manuels, pas des tests).
- Builder l'UI Swift : `cd ui && swift build -c release` → binaire `ui/.build/release/JarvisUI`.
- Logs runtime : `/tmp/jarvis.log` (Python) et stderr du subprocess `claude`.
- **Ne JAMAIS démarrer Jarvis automatiquement** — c'est à l'utilisateur de le lancer.

## Variables d'environnement

`JARVIS_UI` (déf 0 ; 1 = active l'UI Swift), `JARVIS_MODEL` (déf `claude-haiku-4-5`), `JARVIS_KOKORO_VOICE` (déf `ff_siwis`), `JARVIS_KOKORO_SPEED` (déf 1.0), `JARVIS_LOG` (déf `/tmp/jarvis.log`), `JARVIS_NO_COLOR`. Aucune clé API TTS. Pas de `.env` requis pour tourner.

## Profil Claude Code isolé — IMPORTANT

Le backend tourne dans `jarvis_profile/` (cwd) avec `CLAUDE_CONFIG_DIR=jarvis_profile/.claude_home`. La persona / les règles d'oralité / `[FIN]` sont dans `jarvis_profile/CLAUDE.md` ; les permissions dans `jarvis_profile/.claude/settings.json`. `jarvis_profile/.claude_home/` contient l'OAuth et est git-ignoré (ne jamais committer). Auth via `jarvis_profile/login.sh`. Le subprocess est lancé avec `--dangerously-skip-permissions`, donc le bloc allow/deny du settings.json est de fait NON appliqué (Bash a accès complet) — en tenir compte avant de "renforcer" ces deny.

## Protocole UI (sockets Unix, JSON one-shot, fire-and-forget)

- Python → Swift : `/tmp/jarvis-ui.sock`. États orbe : `standby|listening|thinking|speaking` (+ amplitude, tool_name). `question` pour AskUserQuestion.
- Swift → Python : `/tmp/jarvis-ui-events.sock` (`{type:'choice', tool_use_id, label}`), consommé par `assistant.py`.
- Tout est no-op si `JARVIS_UI != 1`. Donc AskUserQuestion sans UI → timeout puis fallback.

## Pièges connus

- `.greeting_cache.npy` : cache régénérable, change à chaque run. Git-ignoré et **détracké** (n'est plus suivi).
- `assistant.reset()` est appelé sans `clear_session=True` → le subprocess n'est jamais redémarré : le contexte conversationnel persiste entre les conversations. (Comportement actuel — à confirmer si voulu.)
- Sockets orphelins dans `/tmp` après un crash : `start.sh` les nettoie au démarrage.
- `ui/Sources/JarvisUI/VibeIsland/ArcReactorState.swift` : nom vestige (l'orbe Fibonacci a remplacé l'Arc Reactor).

## Conventions de commit

Messages en français, conventionnels et scopés : `feat(ui):`, `fix(start):`, `fix(ui):`, `docs:`, `chore:`, `test:` (cf. historique). Commit + push au fil du dev sans demander à chaque fois.
