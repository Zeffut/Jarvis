from __future__ import annotations

from typing import Generator
import anthropic
from config import CLAUDE_MODEL, SYSTEM_PROMPT

# Yielded event types
TOKEN = "token"      # Display immediately
SENTENCE = "sentence"  # Send to TTS


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

    def ask_stream(self, text: str) -> Generator[tuple[str, str], None, None]:
        """Stream response: yields (type, text) where type is TOKEN or SENTENCE."""
        self.history.append({"role": "user", "content": text})

        full_reply = ""
        sentence_buffer = ""

        with self.client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=list(self.history),
        ) as stream:
            for token in stream.text_stream:
                full_reply += token
                sentence_buffer += token

                # Display every token
                yield TOKEN, token

                # Check for sentence end → TTS
                for sep in [".", "!", "?", "\n"]:
                    if sep in sentence_buffer:
                        parts = sentence_buffer.split(sep, 1)
                        sentence = (parts[0] + sep).strip()
                        sentence_buffer = parts[1]
                        if sentence:
                            yield SENTENCE, sentence
                        break

        # Flush remaining buffer
        if sentence_buffer.strip():
            yield SENTENCE, sentence_buffer.strip()

        self.history.append({"role": "assistant", "content": full_reply})

    def reset(self) -> None:
        self.history.clear()
