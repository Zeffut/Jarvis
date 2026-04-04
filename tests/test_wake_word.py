from unittest.mock import patch, MagicMock


def test_wake_word_listener_init():
    with patch("wake_word.WhisperModel"):
        from wake_word import WakeWordListener
        listener = WakeWordListener()
        assert listener.model is not None


def test_wake_word_listener_cleanup():
    with patch("wake_word.WhisperModel"):
        from wake_word import WakeWordListener
        listener = WakeWordListener()
        listener.cleanup()  # should not raise
