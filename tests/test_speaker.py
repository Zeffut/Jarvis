from unittest.mock import patch, MagicMock
import numpy as np


def _make_kokoro_mock(samples=None):
    """Retourne un mock Kokoro.create() qui renvoie des samples valides."""
    if samples is None:
        samples = np.zeros(100, dtype=np.float32)
    mock = MagicMock()
    mock.create.return_value = (samples, 24000)
    return mock


def test_speak_calls_kokoro_create():
    import speaker as spk
    mock_kokoro = _make_kokoro_mock()
    with patch.object(spk, "_get_kokoro", return_value=mock_kokoro):
        with patch.object(spk, "sd"):
            spk.speak("Bonjour Monsieur", wait=False)
    mock_kokoro.create.assert_called_once()
    # text est positionnel, lang est keyword
    assert mock_kokoro.create.call_args[0][0] == "Bonjour Monsieur"
    assert mock_kokoro.create.call_args[1]["lang"] == "fr-fr"


def test_speak_plays_samples_via_sounddevice():
    import speaker as spk
    expected_samples = np.ones(200, dtype=np.float32) * 0.5
    mock_kokoro = _make_kokoro_mock(expected_samples)
    with patch.object(spk, "_get_kokoro", return_value=mock_kokoro):
        with patch.object(spk, "sd") as mock_sd:
            spk.speak("Test", wait=False)
    mock_sd.play.assert_called_once()
    played_samples = mock_sd.play.call_args[0][0]
    np.testing.assert_array_almost_equal(played_samples, expected_samples)
    assert mock_sd.play.call_args[1]["samplerate"] == 24000


def test_preload_greeting_saves_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / ".greeting_cache.npy"
    monkeypatch.setattr("speaker._CACHE_PATH", str(cache_path))
    monkeypatch.setattr("speaker._greeting_samples", None)
    fake_samples = np.zeros(50, dtype=np.float32)
    with patch("speaker._synthesize", return_value=fake_samples):
        from speaker import preload_greeting
        preload_greeting()
    assert cache_path.exists()
    loaded = np.load(str(cache_path))
    np.testing.assert_array_equal(loaded, fake_samples)


def test_preload_greeting_loads_existing_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / ".greeting_cache.npy"
    fake_samples = np.ones(50, dtype=np.float32)
    np.save(str(cache_path), fake_samples)
    monkeypatch.setattr("speaker._CACHE_PATH", str(cache_path))
    monkeypatch.setattr("speaker._greeting_samples", None)
    with patch("speaker._synthesize") as mock_synth:
        from speaker import preload_greeting
        preload_greeting()
        mock_synth.assert_not_called()
