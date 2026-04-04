from unittest.mock import patch, MagicMock


def test_assistant_sends_message_and_returns_response():
    from assistant import Assistant

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Bonjour, comment puis-je vous aider ?")]
    mock_client.messages.create.return_value = mock_response

    with patch("assistant.anthropic.Anthropic", return_value=mock_client):
        asst = Assistant(api_key="test-key")
        reply = asst.ask("Salut Jarvis")

    assert reply == "Bonjour, comment puis-je vous aider ?"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20241001"
    assert len(call_kwargs["messages"]) == 1
    assert call_kwargs["messages"][0]["role"] == "user"
    assert call_kwargs["messages"][0]["content"] == "Salut Jarvis"


def test_assistant_maintains_conversation_history():
    from assistant import Assistant

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Réponse 1")]
    mock_client.messages.create.return_value = mock_response

    with patch("assistant.anthropic.Anthropic", return_value=mock_client):
        asst = Assistant(api_key="test-key")
        asst.ask("Question 1")
        asst.ask("Question 2")

    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]
    assert len(messages) == 3
    assert messages[0] == {"role": "user", "content": "Question 1"}
    assert messages[1] == {"role": "assistant", "content": "Réponse 1"}
    assert messages[2] == {"role": "user", "content": "Question 2"}


def test_assistant_reset_clears_history():
    from assistant import Assistant

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Réponse")]
    mock_client.messages.create.return_value = mock_response

    with patch("assistant.anthropic.Anthropic", return_value=mock_client):
        asst = Assistant(api_key="test-key")
        asst.ask("Question")
        asst.reset()
        asst.ask("Nouvelle question")

    last_call_kwargs = mock_client.messages.create.call_args[1]
    assert len(last_call_kwargs["messages"]) == 1
