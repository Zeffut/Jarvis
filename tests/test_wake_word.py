from unittest.mock import MagicMock


def test_wake_word_listener_init():
    from wake_word import WakeWordListener

    mock_transcriber = MagicMock()
    listener = WakeWordListener(transcriber=mock_transcriber)
    assert listener.transcriber == mock_transcriber


def test_wake_word_listener_cleanup():
    from wake_word import WakeWordListener

    mock_transcriber = MagicMock()
    listener = WakeWordListener(transcriber=mock_transcriber)
    listener.cleanup()  # should not raise
