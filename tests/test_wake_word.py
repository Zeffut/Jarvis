from unittest.mock import patch, MagicMock


def test_wake_word_listener_init():
    from wake_word import WakeWordListener

    mock_porcupine = MagicMock()
    mock_porcupine.frame_length = 512
    mock_porcupine.sample_rate = 16000

    with patch("wake_word.pvporcupine.create", return_value=mock_porcupine) as mock_create:
        listener = WakeWordListener(access_key="test-key")
        mock_create.assert_called_once_with(
            access_key="test-key",
            keywords=["jarvis"],
        )
        assert listener.porcupine == mock_porcupine


def test_wake_word_listener_cleanup():
    from wake_word import WakeWordListener

    mock_porcupine = MagicMock()
    mock_porcupine.frame_length = 512
    mock_porcupine.sample_rate = 16000

    with patch("wake_word.pvporcupine.create", return_value=mock_porcupine):
        listener = WakeWordListener(access_key="test-key")
        listener.cleanup()
        mock_porcupine.delete.assert_called_once()
