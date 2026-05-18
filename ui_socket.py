from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from typing import Callable

SOCKET_PATH = "/tmp/jarvis-ui.sock"
_UI_BINARY = os.path.join(os.path.dirname(__file__), "ui/.build/release/JarvisUI")

_VALID_STATES = frozenset({"standby", "listening", "thinking", "speaking"})

# Toggle UI Swift — OFF par défaut pour focus backend.
# Réactive : JARVIS_UI=1 python3 main.py
UI_ENABLED = os.environ.get("JARVIS_UI", "0") == "1"


def launch_ui() -> None:
    """Lance l'app Swift en arrière-plan si activée et binaire présent."""
    if not UI_ENABLED:
        return
    if os.path.exists(_UI_BINARY):
        subprocess.Popen(
            [_UI_BINARY],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def send_state(state: str, amplitude: float = 0.0, tool_name: str | None = None) -> None:
    """Envoie l'état courant à l'UI Swift. Fire-and-forget, jamais bloquant."""
    if state not in _VALID_STATES:
        return
    _send_to(SOCKET_PATH, state, amplitude, tool_name=tool_name)


def send_display(content: dict) -> None:
    """Envoie un bloc liste/kv/events structuré (zone gauche). Fire-and-forget."""
    _send_to(SOCKET_PATH, "display", 0.0, content=content)


def send_text_start() -> None:
    """Ouvre la zone texte markdown (zone droite)."""
    _send_to(SOCKET_PATH, "text_start", 0.0)


def send_text_token(token: str) -> None:
    """Envoie un fragment de texte à la zone markdown — appelé en temps réel."""
    _send_to(SOCKET_PATH, "text_token", 0.0, token=token)


def send_text_end() -> None:
    """Signale la fin du streaming — déclenche le rendu markdown final."""
    _send_to(SOCKET_PATH, "text_end", 0.0)


def send_browser_open(url: str) -> None:
    """Ouvre le panneau navigateur sur l'URL donnée."""
    _send_to(SOCKET_PATH, "browser_open", 0.0, url=url)


def send_browser_close() -> None:
    """Ferme le panneau navigateur."""
    _send_to(SOCKET_PATH, "browser_close", 0.0)


def _send_to(
    path: str,
    state: str,
    amplitude: float,
    content: dict | None = None,
    token: str | None = None,
    url: str | None = None,
    tool_name: str | None = None,
) -> None:
    """Bas niveau — permet d'injecter un path custom en test."""
    if not UI_ENABLED:
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            s.connect(path)
            payload: dict = {"state": state, "amplitude": round(amplitude, 3)}
            if content is not None:
                payload["content"] = content
            if token is not None:
                payload["token"] = token
            if url is not None:
                payload["url"] = url
            if tool_name is not None:
                payload["tool_name"] = tool_name
            s.sendall(json.dumps(payload).encode())
    except Exception:
        pass


EVENTS_SOCKET_PATH = "/tmp/jarvis-ui-events.sock"


class EventListener:
    """Thread daemon qui écoute /tmp/jarvis-ui-events.sock et appelle
    callback(event_dict) pour chaque message reçu (un par connexion).
    """

    def __init__(self, socket_path: str = EVENTS_SOCKET_PATH,
                 callback: Callable[[dict], None] = lambda e: None):
        self._path = socket_path
        self._callback = callback
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass

    def _run(self) -> None:
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self._path)
        os.chmod(self._path, 0o600)
        self._server.listen(8)
        self._server.settimeout(0.5)
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            if not data:
                continue
            try:
                event = json.loads(data.decode())
            except Exception:
                continue
            try:
                self._callback(event)
            except Exception:
                pass
