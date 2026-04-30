from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Generator, Optional

import jlog

# Frontière de phrase pour le streaming TTS : ponctuation forte suivie
# d'un whitespace, OU une newline seule. Évite de couper "Sonnet 4.6" en
# "Sonnet 4." | "6" — bug observé en prod.
_SENTENCE_BOUNDARY = re.compile(r"[.!?][\s\n]|\n")

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
        jlog.debug("CLAUDE", "warmup ping (cache cold) — start")
        t = time.time()
        try:
            for _ in self.ask_stream("ping", _internal=True):
                pass
            jlog.info("CLAUDE", f"warmup done in {time.time() - t:.2f}s — cache warm")
        except Exception as e:
            jlog.warn("CLAUDE", f"warmup failed: {e}")

    def _keepalive_loop(self) -> None:
        while not self._shutdown_event.is_set():
            if self._shutdown_event.wait(timeout=KEEPALIVE_CHECK):
                return
            elapsed = time.time() - self._last_request_time
            # Skip si une vraie requête a chauffé le cache récemment
            if elapsed < KEEPALIVE_INTERVAL:
                continue
            jlog.debug("CLAUDE", f"keepalive ping (idle {elapsed:.0f}s)")
            try:
                for _ in self.ask_stream("ping", _internal=True):
                    pass
            except Exception as e:
                jlog.warn("CLAUDE", f"keepalive failed: {e}")

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
        # Forcer l'OAuth du profil — sinon une ANTHROPIC_API_KEY shell-level
        # prend priorité et tombe sur "Invalid API key" (cas observé).
        stripped = []
        for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
            if env.pop(k, None) is not None:
                stripped.append(k)
        if stripped:
            jlog.warn("CLAUDE", f"env stripped (préserve OAuth profil): {stripped}")
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
        jlog.info("CLAUDE", f"subprocess up — pid={self._proc.pid}, model={model}, cwd={PROFILE_DIR.name}")
        # NB : claude en mode --input-format=stream-json n'émet rien tant qu'il
        # n'a pas reçu de message utilisateur (pas même l'événement init).
        # Donc on ne bloque PAS ici — le proc est prêt à recevoir, point.

    def _ensure_alive(self) -> None:
        if self._proc is None or self._proc.poll() is not None:
            self._start()

    # ─────────────────────────────────────────────────────────────────
    # API publique
    # ─────────────────────────────────────────────────────────────────

    def ask_stream(
        self,
        text: str,
        *,
        _internal: bool = False,
    ) -> Generator[tuple[str, str], None, None]:
        """Génère TOKEN/SENTENCE/TOOL_USE pour la réponse de Claude.

        `_internal=True` : warm-up / keep-alive — logs en DEBUG, pas de bruit.
        """
        with self._lock:
            self._ensure_alive()
            assert self._proc and self._proc.stdin and self._proc.stdout
            self._last_request_time = time.time()

            if not _internal:
                jlog.info("CLAUDE", f"→ user: {jlog.trunc(text)}")

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
            except (BrokenPipeError, OSError) as e:
                jlog.warn("CLAUDE", f"stdin pipe broken ({e}) — restart subprocess")
                self._start()
                assert self._proc.stdin
                self._proc.stdin.write(user_msg + "\n")
                self._proc.stdin.flush()

            t_start = time.time()
            t_first_token: Optional[float] = None
            full_response = ""
            tools_log: list[str] = []
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
                    if not _internal:
                        # Tente plusieurs schémas (Anthropic / Claude Code)
                        usage = (event.get("usage")
                                 or event.get("message", {}).get("usage")
                                 or {})
                        sub = event.get("subtype", "")
                        result_text = event.get("result", "")
                        jlog.debug(
                            "CLAUDE",
                            f"result subtype={sub!r} "
                            f"in={usage.get('input_tokens', '?')}t "
                            f"out={usage.get('output_tokens', '?')}t "
                            f"cache_read={usage.get('cache_read_input_tokens', '?')}t "
                            f"text={jlog.trunc(str(result_text), 120)!r}"
                        )
                    break

                # ── Streaming temps réel des tokens texte ───────────
                if etype == "stream_event":
                    inner = event.get("event", {})
                    if inner.get("type") == "content_block_delta":
                        delta = inner.get("delta", {})
                        if delta.get("type") == "text_delta":
                            token = delta.get("text", "")
                            if token:
                                if t_first_token is None:
                                    t_first_token = time.time() - t_start
                                full_response += token
                                sentence_buf += token
                                yield TOKEN, token
                                # Cherche TOUTES les frontières dans le buffer
                                # courant — une seule passe de tokens peut
                                # contenir plusieurs phrases si gros chunk.
                                while True:
                                    m = _SENTENCE_BOUNDARY.search(sentence_buf)
                                    if not m:
                                        break
                                    end = m.end()
                                    sentence = sentence_buf[:end].strip()
                                    sentence_buf = sentence_buf[end:]
                                    if sentence:
                                        yield SENTENCE, sentence

                # ── Tool uses + dump des text blocks pour debug ─────
                elif etype == "assistant":
                    msg_content = event.get("message", {}).get("content", [])
                    if not _internal:
                        # Log debug : tous les blocks et leur type
                        for block in msg_content:
                            btype = block.get("type", "?")
                            if btype == "text":
                                jlog.debug("CLAUDE", f"text block: {jlog.trunc(block.get('text', ''), 200)!r}")
                            elif btype == "thinking":
                                jlog.debug("CLAUDE", f"thinking block ({len(block.get('thinking', ''))} chars)")
                            elif btype != "tool_use":
                                jlog.debug("CLAUDE", f"unknown block type={btype}: {jlog.trunc(str(block), 200)}")
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
                        if not _internal:
                            jlog.info("TOOL", f"{tool_name}: {jlog.trunc(str(desc), 100)}")
                        tools_log.append(tool_name)
                        yield TOOL_USE, json.dumps({
                            "name": tool_name,
                            "description": str(desc)[:120],
                        })

            # Reste de buffer non terminé par une ponctuation
            if sentence_buf.strip():
                yield SENTENCE, sentence_buf.strip()

            dt_total = time.time() - t_start
            ft = t_first_token if t_first_token is not None else dt_total
            if _internal:
                jlog.debug("CLAUDE", f"internal ping done in {dt_total:.2f}s")
            else:
                tools_str = f", tools={tools_log}" if tools_log else ""
                jlog.info(
                    "CLAUDE",
                    f"← ({ft:.2f}s 1st / {dt_total:.2f}s tot{tools_str}): "
                    f"{jlog.trunc(full_response) if full_response else '<empty>'}"
                )

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
        jlog.info("CLAUDE", "subprocess shutdown")
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
