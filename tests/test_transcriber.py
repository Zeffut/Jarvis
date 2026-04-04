from unittest.mock import patch, MagicMock
import numpy as np


def test_transcriber_init_loads_model():
    from transcriber import Transcriber

    with patch("transcriber.WhisperModel") as mock_model_cls:
        t = Transcriber(model_size="small")
        mock_model_cls.assert_called_once_with("small", compute_type="auto")


def test_transcribe_returns_text():
    from transcriber import Transcriber

    mock_segment = MagicMock()
    mock_segment.text = " Bonjour Jarvis"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], None)

    with patch("transcriber.WhisperModel", return_value=mock_model):
        t = Transcriber(model_size="small")
        result = t.transcribe(np.zeros(16000, dtype=np.float32))

    assert result == "Bonjour Jarvis"


def test_transcribe_empty_audio_returns_empty_string():
    from transcriber import Transcriber

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([], None)

    with patch("transcriber.WhisperModel", return_value=mock_model):
        t = Transcriber(model_size="small")
        result = t.transcribe(np.zeros(16000, dtype=np.float32))

    assert result == ""
