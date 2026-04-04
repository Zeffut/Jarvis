from __future__ import annotations

import subprocess
import json
from typing import Generator

from config import SYSTEM_PROMPT

# Yielded event types
TOKEN = "token"      # Display immediately
SENTENCE = "sentence"  # Send to TTS


class Assistant:
    def __init__(self, model: str = "haiku"):
        self.model = model
        self.session_id: str | None = None

    def _build_cmd(self, text: str) -> list[str]:
        cmd = [
            "claude",
            "-p", text,
            "--model", self.model,
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
            "--system-prompt", SYSTEM_PROMPT,
        ]
        if self.session_id:
            cmd.extend(["--resume", self.session_id])
        return cmd

    def ask_stream(self, text: str) -> Generator[tuple[str, str], None, None]:
        """Stream response via Claude Code CLI."""
        cmd = self._build_cmd(text)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        full_reply = ""
        sentence_buffer = ""
        last_text_len = 0

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Capture session ID
            if event.get("type") == "system" and "session_id" in event:
                self.session_id = event["session_id"]

            # Extract text from assistant messages (incremental)
            if event.get("type") == "assistant":
                message = event.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "text":
                        full_text = block.get("text", "")
                        # Only yield the new part
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

            # Handle result type (final message)
            if event.get("type") == "result":
                result_text = event.get("result", "")
                if result_text and not full_reply:
                    full_reply = result_text
                    yield TOKEN, result_text
                    yield SENTENCE, result_text

        proc.wait()

        if sentence_buffer.strip():
            yield SENTENCE, sentence_buffer.strip()

    def reset(self) -> None:
        self.session_id = None
