def test_load_config_returns_empty_dict(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.chdir(tmp_path)

    from config import load_config

    cfg = load_config(env_path=str(env_file))
    assert cfg == {}


def test_kokoro_constants_are_set():
    from config import KOKORO_VOICE, KOKORO_SPEED

    assert isinstance(KOKORO_VOICE, str)
    assert len(KOKORO_VOICE) > 0
    assert isinstance(KOKORO_SPEED, float)
    assert KOKORO_SPEED > 0
