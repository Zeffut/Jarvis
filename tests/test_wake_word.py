from unittest.mock import patch, MagicMock


def test_wake_word_listener_init():
    with patch("wake_word.openwakeword") as mock_oww:
        with patch("wake_word.Model") as mock_model_cls:
            from wake_word import WakeWordListener
            listener = WakeWordListener()
            mock_oww.utils.download_models.assert_called_once()
            mock_model_cls.assert_called_once()


def test_wake_word_listener_cleanup():
    with patch("wake_word.openwakeword"):
        with patch("wake_word.Model"):
            from wake_word import WakeWordListener
            listener = WakeWordListener()
            listener.cleanup()  # should not raise
