#!/usr/bin/env python3
"""Lance EventListener, ouvre Vibe Island, pose une question, attend un clic."""
import json
import socket
import time
from ui_socket import EventListener

def on_choice(event):
    print(f"← Reçu : {event}")

listener = EventListener(callback=on_choice)
listener.start()

# Pousse une question vers l'UI
payload = {
    "state": "question",
    "tool_use_id": "toolu_test_roundtrip",
    "question": "Test roundtrip socket — choisis A ou B",
    "choices": [{"id": "0", "label": "A"}, {"id": "1", "label": "B"}],
    "amplitude": 0.0,
}
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect("/tmp/jarvis-ui.sock")
    s.sendall(json.dumps(payload).encode())

print("→ Question envoyée. Clique un bouton dans Vibe Island…")
time.sleep(30)
listener.stop()
