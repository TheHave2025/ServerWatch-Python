"""Validación de variables y ocultamiento de credenciales."""

import pytest

from serverwatch.config import Config, ConfigError


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SW_INTERVAL", "0"),
        ("SW_INTERVAL", "abc"),
        ("SW_CPU_THRESHOLD", "101"),
        ("SW_RAM_THRESHOLD", "-1"),
        ("SW_DISK_THRESHOLD", "mucho"),
        ("SW_TOP_PROCESSES", "-3"),
        ("SW_RECOVERY_MARGIN", "50"),
    ],
)
def test_reject_invalid_values(monkeypatch, tmp_path, name, value):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError):
        Config.from_env()


def test_telegram_requires_both_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SW_TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.delenv("SW_TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(ConfigError, match="ambos"):
        Config.from_env()


def test_public_settings_never_expose_credentials(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SW_TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("SW_TELEGRAM_CHAT_ID", "secret-chat")
    config = Config.from_env()
    assert config.telegram_enabled
    exposed = str(config.public_settings())
    assert "secret-token" not in exposed
    assert "secret-chat" not in exposed


def test_env_file_read_and_env_variable_priority(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SW_INTERVAL=42\nSW_CPU_THRESHOLD=88\n", encoding="utf8")
    monkeypatch.delenv("SW_INTERVAL", raising=False)
    monkeypatch.setenv("SW_CPU_THRESHOLD", "77")
    config = Config.from_env()
    assert config.interval == 42
    assert config.cpu_threshold == 77
