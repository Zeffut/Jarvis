from __future__ import annotations

from typing import Generator
import anthropic
from config import CLAUDE_MODEL, SYSTEM_PROMPT


class Assistant:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict] = []

    def ask(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=list(self.history),
        )

        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def ask_stream(self, text: str) -> Generator[str, None, None]:
        """Stream response sentence by sentence."""
        self.history.append({"role": "user", "content": text})

        full_reply = ""
        buffer = ""

        with self.client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=list(self.history),
        ) as stream:
            for token in stream.text_stream:
                full_reply += token
                buffer += token

                # Yield complete sentences
                for sep in [".", "!", "?", "\n"]:
                    if sep in buffer:
                        parts = buffer.split(sep, 1)
                        sentence = parts[0] + sep
                        buffer = parts[1]
                        sentence = sentence.strip()
                        if sentence:
                            yield sentence
                            break

        # Yield remaining buffer
        if buffer.strip():
            yield buffer.strip()

        self.history.append({"role": "assistant", "content": full_reply})

    def reset(self) -> None:
        self.history.clear()
