#!/usr/bin/env python3
"""Pousse des payloads sur /tmp/jarvis-ui.sock pour tester Vibe Island.
Usage :
  python3 scripts/test_vibe.py <state>
  python3 scripts/test_vibe.py <state> --tool "Gmail · search threads…"
"""

import argparse
import json
import socket

SOCK = "/tmp/jarvis-ui.sock"

def send(payload: dict) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(json.dumps(payload).encode())

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("state")
    ap.add_argument("--tool", default=None)
    ap.add_argument("--question", default=None,
                    help='JSON {"prompt":"...","choices":[{"id":"0","label":"Sarah"}]}')
    ap.add_argument("--tool-use-id", default="toolu_test_123")
    args = ap.parse_args()
    payload = {"state": args.state, "amplitude": 0.0}
    if args.tool:
        payload["tool_name"] = args.tool
    if args.question:
        q = json.loads(args.question)
        payload["state"] = "question"
        payload["tool_use_id"] = args.tool_use_id
        payload["question"] = q["prompt"]
        payload["choices"] = q["choices"]
    print(f"→ {payload}")
    send(payload)
