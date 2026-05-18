"""Test : assistant.py intercepte un tool_use AskUserQuestion et attend
une réponse via EventListener avant d'injecter tool_result."""
import json
import threading
import time

from assistant import Assistant


def test_intercept_askuserquestion_injects_tool_result(monkeypatch):
    """Quand un tool_use AskUserQuestion arrive, le wrapper doit :
    1. Envoyer la question sur le socket UI
    2. Attendre une réponse via EventListener (mockée ici)
    3. Injecter un tool_result dans le stream Claude
    """
    sent_to_ui: list[dict] = []
    injected_to_claude: list[dict] = []

    monkeypatch.setattr(
        "ui_socket.send_question",
        lambda tid, prompt, choices: sent_to_ui.append(
            {"tool_use_id": tid, "prompt": prompt, "choices": choices}
        ),
    )

    # Simuler une réponse utilisateur 0.3s après l'envoi
    def fake_wait(self, tool_use_id: str, timeout: float = 30.0) -> str:
        time.sleep(0.3)
        return "Sarah"

    monkeypatch.setattr(Assistant, "_wait_for_choice", fake_wait, raising=False)

    a = Assistant.__new__(Assistant)
    a._stdin_write_capture = injected_to_claude.append  # type: ignore
    a._handle_askuserquestion(
        tool_id="toolu_xyz",
        question="Mail à Sarah ou Pierre ?",
        options=[
            {"label": "Sarah", "description": "x"},
            {"label": "Pierre", "description": "y"},
        ],
    )

    assert len(sent_to_ui) == 1
    assert sent_to_ui[0]["prompt"] == "Mail à Sarah ou Pierre ?"
    assert sent_to_ui[0]["choices"] == [
        {"id": "0", "label": "Sarah"},
        {"id": "1", "label": "Pierre"},
    ]
    assert len(injected_to_claude) == 1
    parsed = json.loads(injected_to_claude[0].strip())
    assert parsed["type"] == "user"
    content = parsed["message"]["content"][0]
    assert content["type"] == "tool_result"
    assert content["tool_use_id"] == "toolu_xyz"
    assert content["content"] == "Sarah"
