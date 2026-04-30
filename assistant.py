from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Generator, Optional

# Dossier qui contient le profil Jarvis (CLAUDE.md + .claude/settings.json).
# claude tourne avec ce dossier comme cwd → charge le profil project-scoped.
PROFILE_DIR = Path(__file__).parent / "jarvis_profile"

# Config dir isolé : aucun hook, plugin ou MCP global de Thomas n'est chargé.
# → init instantané + comportement déterministe.
# L'auth se fait UNE fois via : CLAUDE_CONFIG_DIR=<ce_path> claude /login
# (ou via ANTHROPIC_API_KEY dans l'env).
CONFIG_DIR = PROFILE_DIR / ".claude_home"

# Modèle utilisé pour Jarvis. Haiku 4.5 = optimisé vitesse pour le vocal
# (~1.5-2s par réponse). Override possible via env JARVIS_MODEL.
DEFAULT_MODEL = "claude-haiku-4-5"

# Log stderr du subprocess claude (debug si quelque chose casse silencieusement).
STDERR_LOG = Path("/tmp/jarvis-claude.log")

# Cache prompt Anthropic = TTL 5 min. On ping toutes les 4 min en idle pour
# garder CLAUDE.md chaud → 1er token toujours ~1.7s même après inactivité.
KEEPALIVE_INTERVAL = 240.0
KEEPALIVE_CHECK    = 60.0

# Yielded event types — contrat inchangé pour main.py.
TOKEN    = "token"
SENTENCE = "sentence"
TOOL_USE = "tool_use"


class Assistant:
    """Subprocess `claude` long-lived en streaming JSON bidirectionnel.

    Lancé UNE seule fois au démarrage de Jarvis. Chaque ask_stream()
    pousse un message utilisateur sur stdin et lit les événements
    jusqu'au 'result' qui termine le tour. Plus de cold-start par tour.
    """

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._stderr_file = open(STDERR_LOG, "w", buffering=1)
        self._shutdown_event = threading.Event()
        self._last_request_time = 0.0
        self._start()
        # Warm-up : ingère CLAUDE.md dans le cache PENDANT que Whisper/Kokoro
        # chargent en parallèle. Au 1er « Jarvis », le cache est déjà chaud.
        threading.Thread(target=self._warmup, daemon=True).start()
        # Keep-alive : ping toutes les 4 min en idle (cache TTL = 5 min).
        threading.Thread(target=self._keepalive_loop, daemon=True).start()

    def _warmup(self) -> None:
        try:
            for _ in self.ask_stream("ping"):
                pass
        except Exception:
            pass

    def _keepalive_loop(self) -> None:
        while not self._shutdown_event.is_set():
            if self._shutdown_event.wait(timeout=KEEPALIVE_CHECK):
                return
            # Skip si une vraie requête a chauffé le cache récemment
            if time.time() - self._last_request_time < KEEPALIVE_INTERVAL:
                continue
            try:
                for _ in self.ask_stream("ping"):
                    pass
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    # Lifecycle subprocess
    # ─────────────────────────────────────────────────────────────────

    def _start(self) -> None:
        model = os.environ.get("JARVIS_MODEL", DEFAULT_MODEL)
        cmd = [
            "claude",
            "--output-format", "stream-json",
            "--input-format",  "stream-json",
            "--include-partial-messages",
            "--verbose",
            "--dangerously-skip-permissions",
            "--model", model,
        ]
        # Env isolé : pas de hooks/plugins/MCPs globaux → init quasi-instantané.
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(CONFIG_DIR)
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(PROFILE_DIR),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr_file,
            text=True,
            bufsize=1,
        )
        # NB : claude en mode --input-format=stream-json n'émet rien tant qu'il
        # n'a pas reçu de message utilisateur (pas même l'événement init).
        # Donc on ne bloque PAS ici — le proc est prêt à recevoir, point.

    def _ensure_alive(self) -> None:
        if self._proc is None or self._proc.poll() is not None:
            self._start()

    # ─────────────────────────────────────────────────────────────────
    # API publique
    # ─────────────────────────────────────────────────────────────────

    def ask_stream(self, text: str) -> Generator[tuple[str, str], None, None]:
        with self._lock:
            self._ensure_alive()
            assert self._proc and self._proc.stdin and self._proc.stdout
            self._last_request_time = time.time()

            # Pousser le message utilisateur sur stdin
            user_msg = json.dumps({
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": text}],
                },
            })
            try:
                self._proc.stdin.write(user_msg + "\n")
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError):
                # Le proc est mort — relance puis réessaye
                self._start()
                assert self._proc.stdin
                self._proc.stdin.write(user_msg + "\n")
                self._proc.stdin.flush()

            sentence_buf = ""
            seen_tools: set[str] = set()

            for line in self._proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type")

                # ── Fin du tour ──────────────────────────────────────
                if etype == "result":
                    break

                # ── Streaming temps réel des tokens texte ───────────
                if etype == "stream_event":
                    inner = event.get("event", {})
                    if inner.get("type") == "content_block_delta":
                        delta = inner.get("delta", {})
                        if delta.get("type") == "text_delta":
                            token = delta.get("text", "")
                            if token:
                                sentence_buf += token
                                yield TOKEN, token
                                for sep in (".", "!", "?", "\n"):
                                    if sep in sentence_buf:
                                        parts = sentence_buf.split(sep, 1)
                                        sentence = (parts[0] + sep).strip()
                                        sentence_buf = parts[1]
                                        if sentence:
                                            yield SENTENCE, sentence
                                        break

                # ── Tool uses (1 par bloc, dédup par id) ────────────
                elif etype == "assistant":
                    msg_content = event.get("message", {}).get("content", [])
                    for block in msg_content:
                        if block.get("type") != "tool_use":
                            continue
                        tool_id = block.get("id", "")
                        if tool_id and tool_id in seen_tools:
                            continue
                        if tool_id:
                            seen_tools.add(tool_id)
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {}) or {}
                        desc = (
                            tool_input.get("description")
                            or tool_input.get("command")
                            or tool_input.get("query")
                            or tool_input.get("url")
                            or tool_input.get("pattern")
                            or tool_input.get("path")
                            or tool_input.get("file_path")
                            or ""
                        )
                        yield TOOL_USE, json.dumps({
                            "name": tool_name,
                            "description": str(desc)[:120],
                        })

            # Reste de buffer non terminé par une ponctuation
            if sentence_buf.strip():
                yield SENTENCE, sentence_buf.strip()

    def reset(self, clear_session: bool = False) -> None:
        """Le subprocess reste warm. On NE redémarre PAS — le contexte
        persistant entre invocations vocales est intentionnel : Jarvis
        garde le fil entre deux wakes consécutifs.

        Si `clear_session=True`, on tue et on relance pour repartir vierge.
        """
        if not clear_session:
            return
        with self._lock:
            if self._proc:
                try:
                    if self._proc.stdin:
                        self._proc.stdin.close()
                except Exception:
                    pass
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                self._proc = None
            self._start()

    def shutdown(self) -> None:
        """Arrêt propre — appelé à la fermeture de Jarvis."""
        self._shutdown_event.set()
        with self._lock:
            if self._proc and self._proc.poll() is None:
                try:
                    if self._proc.stdin:
                        self._proc.stdin.close()
                except Exception:
                    pass
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None
            try:
                self._stderr_file.close()
            except Exception:
                pass
