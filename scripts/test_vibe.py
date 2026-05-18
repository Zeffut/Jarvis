#!/usr/bin/env python3
"""Pousse des payloads sur /tmp/jarvis-ui.sock pour tester Vibe Island
sans lancer Whisper/Kokoro. Usage : python3 scripts/test_vibe.py <state>"""

import json
import socket
import sys

SOCK = "/tmp/jarvis-ui.sock"

def send(payload: dict) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(json.dumps(payload).encode())

if __name__ == "__main__":
    state = sys.argv[1] if len(sys.argv) > 1 else "standby"
    payload = {"state": state, "amplitude": 0.0}
    print(f"→ {payload}")
    send(payload)
