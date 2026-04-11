from __future__ import annotations

import subprocess
import json
import os
import threading
from typing import Generator

from config import SYSTEM_PROMPT

# Yielded event types
TOKEN = "token"
SENTENCE = "sentence"
TOOL_USE = "tool_use"

_CREDIT_ERROR = "credit balance is too low"


class Assistant:
    def __init__(self, model: str = "sonnet"):
        self.model = model
        self._session_id: str | None = None
        self._lock = threading.Lock()  # protège _session_id

    def _build_cmd(self, text: str, session_id: str | None = None) -> list[str]:
        cmd = [
            "claude", "-p", text,
            "--model", self.model,
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
            "--append-system-prompt", SYSTEM_PROMPT,
        ]
        if session_id:
            cmd += ["--resume", session_id]
        return cmd

    def _run(self, text: str, session_id: str | None) -> Generator[tuple[str, str], None, None]:
        import time

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        cmd = self._build_cmd(text, session_id)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,   # PIPE jamais lu = deadlock potentiel
            text=True,
            env=env,
        )

        lines_buf: list[str] = []
        buf_lock = threading.Lock()

        def reader():
            for line in proc.stdout:
                line = line.strip()
                if line:
                    with buf_lock:
                        lines_buf.append(line)

        threading.Thread(target=reader, daemon=True).start()

        full_reply = ""
        sentence_buffer = ""
        last_text_len = 0
        got_result = False
        new_session_id: str | None = None
        deadline = time.time() + 120

        while not got_result:
            if proc.poll() is not None and not lines_buf:
                break
            if time.time() > deadline:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break

            time.sleep(0.05)

            with buf_lock:
                lines = lines_buf.copy()
                lines_buf.clear()

            for line in lines:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type")

                if etype in ("system", "result"):
                    sid = event.get("session_id") or event.get("sessionId")
                    if sid:
                        new_session_id = sid

                if etype == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            tool_input = block.get("input", {})
                            desc = (
                                tool_input.get("description", "")
                                or tool_input.get("command", "")
                                or ""
                            )
                            yield TOOL_USE, json.dumps({"name": tool_name, "description": desc})

                        if block.get("type") == "text":
                            full_text = block.get("text", "")
                            new_text = full_text[last_text_len:]
                            last_text_len = len(full_text)
                            if not new_text:
                                continue

                            full_reply += new_text
                            sentence_buffer += new_text
                            yield TOKEN, new_text

                            for sep in (".", "!", "?", "\n"):
                                if sep in sentence_buffer:
                                    parts = sentence_buffer.split(sep, 1)
                                    sentence = (parts[0] + sep).strip()
                                    sentence_buffer = parts[1]
                                    if sentence:
                                        yield SENTENCE, sentence
                                    break

                if etype == "result":
                    got_result = True
                    last_text_len = 0
                    result_text = event.get("result", "")
                    if result_text and not full_reply:
                        full_reply = result_text
                        yield TOKEN, result_text
                        sentence_buffer += result_text

        # Attendre la fin du processus avec timeout
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        if sentence_buffer.strip():
            yield SENTENCE, sentence_buffer.strip()

        with self._lock:
            self._last_session_id = new_session_id
            self._last_reply = full_reply

    def ask_stream(self, text: str) -> Generator[tuple[str, str], None, None]:
        """Stream la réponse en temps réel. Gère le fallback crédit après coup."""
        with self._lock:
            self._last_session_id = None
            self._last_reply = ""
            session_id = self._session_id

        yield from self._run(text, session_id)

        with self._lock:
            full = self._last_reply.lower()
            if _CREDIT_ERROR in full and self._session_id:
                self._session_id = None
            elif self._last_session_id:
                self._session_id = self._last_session_id

    def reset(self, clear_session: bool = False) -> None:
        if clear_session:
            with self._lock:
                self._session_id = None
