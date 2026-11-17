"""Servidor HTTP nativo para el panel, sin dependencias web adicionales.

Por defecto escucha 127.0.0.1. Para acceso externo se recomienda túnel SSH
sobre HTTPS reverse proxy. API de ingreso requiere token Bearer.
"""

import base64
import binascii
import json
import logging
import secrets
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .alerts import AlertTracker
from .collector import collect_snapshot
from .config import Config
from .models import AlertEvent, Snapshot
from .remote import PayloadError, validate_snapshot
from .storage import Database
from .telegram import NotificationError, TelegramNotifier

log = logging.getLogger("serverwatch")


class Hub:
    """Estado compartido entre web y recolección local protegido con mutex."""

    def __init__(self, config: Config, database: Database):
        self.config = config
        self.database = database
        self.trackers: dict[str, AlertTracker] = {}
        self.lock = threading.RLock()

    def ingest(self, snapshot: Snapshot) -> None:
        with self.lock:
            tracker = self.trackers.setdefault(snapshot.hostname, AlertTracker(self.config))
            events = tracker.evaluate(snapshot)
            self.database.save(snapshot, events)
        if self.config.telegram_enabled and events:
            threading.Thread(target=self._notify, args=(events,), daemon=True).start()

    def _notify(self, events: list[AlertEvent]) -> None:
        notifier = TelegramNotifier(self.config.telegram_token, self.config.telegram_chat_id)
        for event in events:
            try:
                notifier.send_alert(event)
            except NotificationError:
                log.warning("No se pudo enviar aviso a Telegram")

    def collect_local_forever(self, stop: threading.Event) -> None:
        tick = 0
        while not stop.is_set():
            try:
                snapshot = collect_snapshot(
                    self.config.disk_path, self.config.top_processes,
                    self.config.cpu_sample_seconds, services=self.config.services,
                )
                if self.config.node_name:
                    snapshot = replace(snapshot, hostname=self.config.node_name)
                self.ingest(snapshot)
                if tick % 100 == 0:
                    self.database.prune(self.config.retention_days)
                tick += 1
            except Exception:
                log.exception("Fallo temporal de recolección local")
            if stop.wait(self.config.interval):
                break


def build_handler(hub: Hub) -> type[BaseHTTPRequestHandler]:
    """Construye un handler acoplado exclusivamente al Hub proporcionado."""
    dashboard_html = Path(__file__).with_name("dashboard.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        server_version = "ServerWatch/2.0"
        sys_version = ""

        def log_message(self, format, *args):
            log.info("HTTP %s - %s", self.client_address[0], format % args)

        def _send(self, status: int, body: bytes, content_type: str, extra: dict = None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj: object):
            self._send(status, json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")

        def _ui_authorized(self):
            if not hub.config.dashboard_password:
                return True
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Basic "):
                return False
            try:
                supplied = base64.b64decode(auth[6:], validate=True).decode("utf-8")
                name, password = supplied.split(":", 1)
            except (ValueError, UnicodeError, binascii.Error):
                return False
            return secrets.compare_digest(name, "serverwatch") and secrets.compare_digest(password, hub.config.dashboard_password)

        def _require_ui(self):
            if self._ui_authorized():
                return True
            self._json(401, {"error": "Se requiere autenticación"})
            return False

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._json(200, {"status": "ok"})
                return
            if not self._ui_authorized():
                body = b"Authentication required"
                self._send(401, body, "text/plain; charset=utf-8", {"WWW-Authenticate": 'Basic realm="ServerWatch Dashboard", charset="UTF-8"'})
                return
            if parsed.path == "/":
                self._send(200, dashboard_html, "text/html; charset=utf-8")
            elif parsed.path == "/api/overview":
                self._json(200, {"servers": hub.database.servers(hub.config.offline_after),
                                 "timestamp": int(time.time()), "offline_after": hub.config.offline_after})
            elif parsed.path == "/api/history":
                q = parse_qs(parsed.query)
                node = q.get("server", [""])[0]
                if len(node) > 64:
                    self._json(400, {"error": "Servidor inválido"})
                    return
                try:
                    limit = int(q.get("limit", ["120"])[0])
                except ValueError:
                    self._json(400, {"error": "Limit inválido"})
                    return
                self._json(200, {"server": node, "points": hub.database.history(node, limit)})
            elif parsed.path == "/api/events":
                self._json(200, {"events": hub.database.events(40)})
            else:
                self._json(404, {"error": "Ruta desconocida"})

        def do_POST(self):
            if urlparse(self.path).path != "/api/ingest":
                self._json(404, {"error": "Ruta desconocida"})
                return
            token = hub.config.ingest_token
            if not token:
                self._json(503, {"error": "Ingesta no habilitada"})
                return
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or not secrets.compare_digest(auth[7:], token):
                self._json(401, {"error": "No autorizado"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].lower() != "application/json":
                self._json(415, {"error": "Content-Type debe ser application/json"})
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._json(411, {"error": "Content-Length inválido"})
                return
            if length <= 0 or length > 30_000:
                self._json(413, {"error": "Payload fuera de tamaño permitido"})
                return
            try:
                content = self.rfile.read(length)
                payload = json.loads(content)
                snapshot = validate_snapshot(payload)
            except (ValueError, UnicodeError, PayloadError):
                self._json(400, {"error": "Muestra inválida"})
                return
            try:
                hub.ingest(snapshot)
            except Exception:
                log.exception("Fallo guardando muestra")
                self._json(500, {"error": "No se pudo guardar"})
                return
            self._json(202, {"accepted": True})

    return Handler


def create_server(config: Config, database: Database = None) -> tuple[ThreadingHTTPServer, Hub]:
    database = database or Database(config.database)
    hub = Hub(config, database)
    server = ThreadingHTTPServer((config.dashboard_host, config.dashboard_port), build_handler(hub))
    server.daemon_threads = True
    return server, hub


def serve_dashboard(config: Config) -> None:
    server, hub = create_server(config)
    stop = threading.Event()
    thread = threading.Thread(target=hub.collect_local_forever, args=(stop,), daemon=True)
    thread.start()
    print(f"ServerWatch 2.0: panel en http://{config.dashboard_host}:{config.dashboard_port} (Ctrl+C para salir)", flush=True)
    try:
        server.serve_forever(poll_interval=0.4)
    finally:
        stop.set()
        server.server_close()
        thread.join(timeout=2)
