from __future__ import annotations

import subprocess
import json
import threading
from typing import Generator

from config import SYSTEM_PROMPT

# Yielded event types
TOKEN = "token"
SENTENCE = "sentence"


class Assistant:
    def __init__(self, model: str = "haiku"):
        self.model = model
        self.proc: subprocess.Popen | None = None
        self._reader_lines: list[str] = []
        self._reader_lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._start_process()

    def _start_process(self):
        """Start a persistent Claude Code process."""
        cmd = [
            "claude",
            "-p",
            "--model", self.model,
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
            "--append-system-prompt", SYSTEM_PROMPT,
        ]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # Start background reader thread
        self._reader_lines = []
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

    def _read_stdout(self):
        """Continuously read stdout lines into buffer."""
        for line in self.proc.stdout:
            line = line.strip()
            if line:
                with self._reader_lock:
                    self._reader_lines.append(line)

    def _get_lines(self) -> list[str]:
        with self._reader_lock:
            lines = self._reader_lines.copy()
            self._reader_lines.clear()
        return lines

    def _send_message(self, text: str):
        """Send a user message via stdin."""
        msg = json.dumps({"type": "user_message", "content": text})
        self.proc.stdin.write(msg + "\n")
        self.proc.stdin.flush()

    def ask_stream(self, text: str) -> Generator[tuple[str, str], None, None]:
        """Send message and stream response tokens."""
        import time

        # Restart process if dead
        if self.proc is None or self.proc.poll() is not None:
            self._start_process()

        # Clear any pending output
        self._get_lines()

        self._send_message(text)

        full_reply = ""
        sentence_buffer = ""
        last_text_len = 0
        got_result = False

        while not got_result:
            time.sleep(0.05)
            lines = self._get_lines()

            for line in lines:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract incremental text from assistant messages
                if event.get("type") == "assistant":
                    message = event.get("message", {})
                    for block in message.get("content", []):
                        if block.get("type") == "text":
                            full_text = block.get("text", "")
                            new_text = full_text[last_text_len:]
                            last_text_len = len(full_text)

                            if not new_text:
                                continue

                            full_reply += new_text
                            sentence_buffer += new_text

                            yield TOKEN, new_text

                            for sep in [".", "!", "?", "\n"]:
                                if sep in sentence_buffer:
                                    parts = sentence_buffer.split(sep, 1)
                                    sentence = (parts[0] + sep).strip()
                                    sentence_buffer = parts[1]
                                    if sentence:
                                        yield SENTENCE, sentence
                                    break

                # End of turn
                if event.get("type") == "result":
                    got_result = True
                    # Reset text tracking for next message
                    last_text_len = 0

                    # Handle case where result has text but nothing was streamed
                    result_text = event.get("result", "")
                    if result_text and not full_reply:
                        full_reply = result_text
                        yield TOKEN, result_text
                        sentence_buffer += result_text

        if sentence_buffer.strip():
            yield SENTENCE, sentence_buffer.strip()

    def reset(self) -> None:
        """Kill the process and start fresh for a new conversation."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait()
        self.proc = None
        self._reader_lines = []

    def __del__(self):
        self.reset()
