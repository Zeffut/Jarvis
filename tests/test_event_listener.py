"""Tests pour EventListener côté Python (lit /tmp/jarvis-ui-events.sock)."""
import json
import os
import socket
import tempfile
import threading
import time

import pytest

from ui_socket import EventListener


def test_event_listener_captures_choice():
    """EventListener doit recevoir un payload choice et le passer au callback."""
    # tmp_path dépasse souvent 104 chars (limite AF_UNIX macOS) — utiliser /tmp
    sock_path = "/tmp/test_jarvis_events_{}.sock".format(os.getpid())
    received: list[dict] = []
    done = threading.Event()

    def on_event(event: dict):
        received.append(event)
        done.set()

    listener = EventListener(socket_path=sock_path, callback=on_event)
    listener.start()
    try:
        # Attendre que le socket soit bind
        for _ in range(20):
            if os.path.exists(sock_path):
                break
            time.sleep(0.05)
        assert os.path.exists(sock_path), "EventListener n'a pas bind le socket"

        # Envoyer un payload
        payload = {"type": "choice", "tool_use_id": "tool_abc", "label": "Sarah"}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(sock_path)
            s.sendall(json.dumps(payload).encode())

        assert done.wait(timeout=2.0), "Callback non appelé"
        assert received == [payload]
    finally:
        listener.stop()
