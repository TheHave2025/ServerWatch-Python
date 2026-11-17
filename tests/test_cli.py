"""Pruebas básicas de CLI sin enviar datos externos."""

import json

from serverwatch.cli import main


def test_config_command(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SW_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SW_TELEGRAM_CHAT_ID", raising=False)
    assert main(["config"]) == 0
    settings = json.loads(capsys.readouterr().out)
    assert settings["telegram_enabled"] is False


def test_once_json(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SW_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SW_TELEGRAM_CHAT_ID", raising=False)
    assert main(["once", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert "snapshot" in result
    assert "events" in result


def test_notify_test_without_credentials(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SW_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SW_TELEGRAM_CHAT_ID", raising=False)
    assert main(["notify-test"]) == 2
    assert "Error:" in capsys.readouterr().err
