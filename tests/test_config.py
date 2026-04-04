import os
import pytest


def test_load_config_returns_required_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-anthropic-key\nPICOVOICE_ACCESS_KEY=test-pico-key\n"
    )
    monkeypatch.chdir(tmp_path)
    # Clean environment before test
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PICOVOICE_ACCESS_KEY", raising=False)

    from config import load_config

    cfg = load_config(env_path=str(env_file))
    assert cfg["anthropic_api_key"] == "test-anthropic-key"
    assert cfg["picovoice_access_key"] == "test-pico-key"


def test_load_config_raises_on_missing_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-key\n")
    monkeypatch.chdir(tmp_path)
    # Clean environment before test
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PICOVOICE_ACCESS_KEY", raising=False)

    from config import load_config

    with pytest.raises(ValueError, match="PICOVOICE_ACCESS_KEY"):
        load_config(env_path=str(env_file))
