def test_load_config_loads_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("JARVIS_TEST_VAR=hello\n")
    monkeypatch.delenv("JARVIS_TEST_VAR", raising=False)

    from config import load_config

    # load_config charge le .env par effet de bord et ne retourne rien.
    result = load_config(env_path=str(env_file))
    assert result is None

    import os
    assert os.environ.get("JARVIS_TEST_VAR") == "hello"


def test_kokoro_constants_are_set():
    from config import KOKORO_VOICE, KOKORO_SPEED

    assert isinstance(KOKORO_VOICE, str)
    assert len(KOKORO_VOICE) > 0
    assert isinstance(KOKORO_SPEED, float)
    assert KOKORO_SPEED > 0
