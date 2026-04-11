from __future__ import annotations

import json
import os
import socket
import subprocess

SOCKET_PATH = "/tmp/jarvis-ui.sock"
_UI_BINARY = os.path.join(os.path.dirname(__file__), "ui/.build/release/JarvisUI")


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
    _send_to(SOCKET_PATH, state, amplitude)


def _send_to(path: str, state: str, amplitude: float) -> None:
    """Bas niveau — permet d'injecter un path custom en test."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
            s.connect(path)
            s.sendall(json.dumps({"state": state, "amplitude": round(amplitude, 3)}).encode())
    except Exception:
        pass
