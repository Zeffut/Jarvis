import os
import pytest


def test_load_config_returns_required_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ELEVENLABS_API_KEY=test-eleven-key\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    from config import load_config

    cfg = load_config(env_path=str(env_file))
    assert cfg["elevenlabs_api_key"] == "test-eleven-key"


def test_load_config_raises_on_missing_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    from config import load_config

    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        load_config(env_path=str(env_file))
