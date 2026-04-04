from unittest.mock import patch, MagicMock
import numpy as np


def _make_mock_file():
    mock_file = MagicMock()
    mock_file.__enter__ = MagicMock(return_value=mock_file)
    mock_file.__exit__ = MagicMock(return_value=False)
    mock_file.name = "/tmp/test.wav"
    return mock_file


@patch("transcriber.os")
@patch("transcriber.sf")
@patch("transcriber.mlx_whisper")
@patch("transcriber.tempfile")
def test_transcriber_init(mock_tmp, mock_mlx, mock_sf, mock_os):
    mock_tmp.NamedTemporaryFile.return_value = _make_mock_file()
    mock_mlx.transcribe.return_value = {"text": ""}

    from transcriber import Transcriber
    t = Transcriber(model="mlx-community/whisper-turbo")
    assert t.model == "mlx-community/whisper-turbo"


@patch("transcriber.os")
@patch("transcriber.sf")
@patch("transcriber.mlx_whisper")
@patch("transcriber.tempfile")
def test_transcribe_returns_text(mock_tmp, mock_mlx, mock_sf, mock_os):
    mock_tmp.NamedTemporaryFile.return_value = _make_mock_file()
    mock_mlx.transcribe.return_value = {"text": " Bonjour comment ça va "}

    from transcriber import Transcriber
    t = Transcriber(model="mlx-community/whisper-turbo")
    result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert result == "Bonjour comment ça va"


@patch("transcriber.os")
@patch("transcriber.sf")
@patch("transcriber.mlx_whisper")
@patch("transcriber.tempfile")
def test_transcribe_empty_returns_empty(mock_tmp, mock_mlx, mock_sf, mock_os):
    mock_tmp.NamedTemporaryFile.return_value = _make_mock_file()
    mock_mlx.transcribe.return_value = {"text": ""}

    from transcriber import Transcriber
    t = Transcriber(model="mlx-community/whisper-turbo")
    result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert result == ""
