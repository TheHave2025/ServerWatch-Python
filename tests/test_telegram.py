"""Telegram se simula completamente; nunca se abre una conexión real."""

import io
import json

import pytest

from serverwatch.models import AlertEvent
from serverwatch.telegram import NotificationError, TelegramNotifier, format_telegram_alert


class FakeResponse:
    def __init__(self, result):
        self._body = io.BytesIO(json.dumps(result).encode())

    def __enter__(self):
        return self._body

    def __exit__(self, exc_type, exc, tb):
        self._body.close()


def test_message_payload_is_posted(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse({"ok": True})

    monkeypatch.setattr("serverwatch.telegram.urlopen", fake_urlopen)
    TelegramNotifier("test-token", "-100111").send_message("Hola")
    req, timeout = requests[0]
    body = json.loads(req.data)
    assert req.get_method() == "POST"
    assert body["chat_id"] == "-100111"
    assert body["text"] == "Hola"
    assert timeout == 10


def test_telegram_error_hides_token(monkeypatch):
    def fails(*args, **kwargs):
        raise OSError("sin red")

    monkeypatch.setattr("serverwatch.telegram.urlopen", fails)
    with pytest.raises(NotificationError) as err:
        TelegramNotifier("very-secret", "-101").send_message("Prueba")
    assert "very-secret" not in str(err.value)


def test_telegram_api_rejects(monkeypatch):
    monkeypatch.setattr(
        "serverwatch.telegram.urlopen", lambda request, timeout: FakeResponse({"ok": False})
    )
    with pytest.raises(NotificationError):
        TelegramNotifier("test", "chat").send_message("Hola")


def test_html_escapes_hostnames():
    event = AlertEvent(
        metric="cpu", status="triggered", value=93, threshold=90,
        hostname="host&<bad>", timestamp="2026-11-17T12:00:00+00:00"
    )
    text = format_telegram_alert(event)
    assert "host&amp;&lt;bad&gt;" in text
    assert "<bad>" not in text
    assert "93.0%" in text
