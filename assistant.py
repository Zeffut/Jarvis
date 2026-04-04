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

    def reset(self) -> None:
        self.history.clear()
