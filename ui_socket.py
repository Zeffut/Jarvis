from __future__ import annotations

import json
import os
import socket
import subprocess

SOCKET_PATH = "/tmp/jarvis-ui.sock"
_UI_BINARY = os.path.join(os.path.dirname(__file__), "ui/.build/release/JarvisUI")

_VALID_STATES = frozenset({"standby", "listening", "thinking", "speaking"})


def launch_ui() -> None:
    """Lance l'app Swift en arrière-plan si le binaire est présent."""
    if os.path.exists(_UI_BINARY):
        subprocess.Popen(
            [_UI_BINARY],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def send_state(state: str, amplitude: float = 0.0) -> None:
    """Envoie l'état courant à l'UI Swift. Fire-and-forget, jamais bloquant."""
    if state not in _VALID_STATES:
        return
    _send_to(SOCKET_PATH, state, amplitude)


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
) -> None:
    """Bas niveau — permet d'injecter un path custom en test."""
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
            s.sendall(json.dumps(payload).encode())
    except Exception:
        pass
