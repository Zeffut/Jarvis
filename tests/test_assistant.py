from unittest.mock import patch, MagicMock


def test_assistant_sends_message_and_returns_response():
    from assistant import Assistant

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Bonjour!"}}]
    }

    with patch("assistant.requests.post", return_value=mock_response) as mock_post:
        asst = Assistant(base_url="http://localhost:18789", auth_token="test")
        reply = asst.ask("Salut")

    assert reply == "Bonjour!"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["json"]["model"] == "openclaw/default"


def test_assistant_maintains_conversation_history():
    from assistant import Assistant

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Réponse"}}]
    }

    with patch("assistant.requests.post", return_value=mock_response):
        asst = Assistant(base_url="http://localhost:18789", auth_token="test")
        asst.ask("Question 1")
        asst.ask("Question 2")

    assert len(asst.history) == 4  # 2 user + 2 assistant


def test_assistant_reset_clears_history():
    from assistant import Assistant

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Réponse"}}]
    }

    with patch("assistant.requests.post", return_value=mock_response):
        asst = Assistant(base_url="http://localhost:18789", auth_token="test")
        asst.ask("Question")
        asst.reset()

    assert len(asst.history) == 0
