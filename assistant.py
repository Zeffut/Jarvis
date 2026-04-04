from __future__ import annotations

from typing import Generator
import requests
import json

from config import SYSTEM_PROMPT

# Yielded event types
TOKEN = "token"      # Display immediately
SENTENCE = "sentence"  # Send to TTS


class Assistant:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.history: list[dict] = []

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def ask(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(self.history)

        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self._headers(),
            json={
                "model": "openclaw/default",
                "messages": messages,
                "max_tokens": 150,
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def ask_stream(self, text: str) -> Generator[tuple[str, str], None, None]:
        """Stream response: yields (type, text) where type is TOKEN or SENTENCE."""
        self.history.append({"role": "user", "content": text})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(self.history)

        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self._headers(),
            json={
                "model": "openclaw/default",
                "messages": messages,
                "max_tokens": 150,
                "stream": True,
            },
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()

        full_reply = ""
        sentence_buffer = ""

        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break

            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content", "")
            if not token:
                continue

            full_reply += token
            sentence_buffer += token

            yield TOKEN, token

            for sep in [".", "!", "?", "\n"]:
                if sep in sentence_buffer:
                    parts = sentence_buffer.split(sep, 1)
                    sentence = (parts[0] + sep).strip()
                    sentence_buffer = parts[1]
                    if sentence:
                        yield SENTENCE, sentence
                    break

        if sentence_buffer.strip():
            yield SENTENCE, sentence_buffer.strip()

        self.history.append({"role": "assistant", "content": full_reply})

    def reset(self) -> None:
        self.history.clear()
