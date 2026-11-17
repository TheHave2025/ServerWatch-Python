"""Cliente sencillo y opcional para Telegram Bot API.

Usa únicamente HTTPS saliente, sin servidor web, webhook ni dependencias HTTP
adicionales. No registra ni devuelve el token en excepciones públicas.
"""

import json
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import AlertEvent


class NotificationError(RuntimeError):
    """Fallo entregando mensaje a Telegram sin exponer credenciales."""


_METRIC_NAMES = {"cpu": "CPU", "ram": "RAM", "disk": "Disco"}
_STATUS_NAMES = {
    "triggered": ("🚨", "ALERTA"),
    "reminder": ("⏰", "RECORDATORIO"),
    "recovered": ("✅", "RECUPERACIÓN"),
}


def format_telegram_alert(event: AlertEvent) -> str:
    icon, status = _STATUS_NAMES[event.status]
    if event.metric.startswith("service:"):
        return (f"{icon} <b>ServerWatch: {status}</b>\n"
                f"Servidor: <code>{escape(event.hostname)}</code>\n"
                f"Servicio: <code>{escape(event.metric[8:])}</code>\n"
                f"Estado: {'INACTIVO' if event.status != 'recovered' else 'ACTIVO'}\n"
                f"Hora: {escape(event.timestamp)}")
    return (
        f"{icon} <b>ServerWatch: {status}</b>\n"
        f"Servidor: <code>{escape(event.hostname)}</code>\n"
        f"Recurso: <b>{_METRIC_NAMES[event.metric]}</b>\n"
        f"Uso actual: <b>{event.value:.1f}%</b>\n"
        f"Umbral: {event.threshold:.1f}%\n"
        f"Hora: {escape(event.timestamp)}"
    )


class TelegramNotifier:
    """Envia mensajes de texto al chat configurado mediante Bot API."""

    def __init__(self, token: str, chat_id: str, timeout: float = 10) -> None:
        self._token = token
        self._chat_id = chat_id
        self._timeout = timeout

    def send_message(self, html_text: str) -> None:
        payload = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": html_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{self._token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                result = json.load(response)
            if not result.get("ok"):
                raise NotificationError("Telegram rechazó el mensaje; revisa bot y chat ID")
        except (HTTPError, URLError, OSError, TimeoutError, ValueError):
            # No interpolar nunca la URL: contiene el token del bot.
            raise NotificationError(
                "No se pudo enviar la alerta a Telegram; revisa conexión y credenciales"
            ) from None

    def send_alert(self, event: AlertEvent) -> None:
        self.send_message(format_telegram_alert(event))
