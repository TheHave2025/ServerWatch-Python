"""Protocolo de telemetría de agente a central. HTTPS + Bearer token."""

import json
import math
import ssl
from dataclasses import asdict
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler

from .models import ProcessInfo, ServiceStatus, Snapshot


class PayloadError(ValueError):
    """Datos remotos inválidos o incompletos."""


def _value(data: dict, key: str, low: float = 0, high: float = 1e16) -> float:
    obj = data.get(key)
    if isinstance(obj, bool) or not isinstance(obj, (float, int)):
        raise PayloadError(f"{key}: número requerido")
    value = float(obj)
    if not math.isfinite(value) or not low <= value <= high:
        raise PayloadError(f"{key}: fuera de rango")
    return value


def validate_snapshot(data: object) -> Snapshot:
    """Valida cada campo antes de insertarlo en SQLite; no ejecuta datos remotos."""
    if not isinstance(data, dict):
        raise PayloadError("Se requiere un objeto JSON")
    host = data.get("hostname")
    import re
    if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", host):
        raise PayloadError("hostname inválido")
    stamp = data.get("timestamp")
    try:
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None or len(stamp) > 64:
            raise ValueError("time zone required")
    except (TypeError, ValueError) as exc:
        raise PayloadError("timestamp ISO-8601 con zona horaria requerido") from exc
    disk_path = data.get("disk_path")
    if not isinstance(disk_path, str) or not 1 <= len(disk_path) <= 256:
        raise PayloadError("disk_path inválido")
    load = []
    for key in ("load_1m", "load_5m", "load_15m"):
        load.append(None if data.get(key) is None else _value(data, key, 0, 100000))
    raw_processes = data.get("top_processes", [])
    raw_services = data.get("services", [])
    if not isinstance(raw_processes, (tuple, list)) or len(raw_processes) > 30:
        raise PayloadError("top_processes inválido")
    if not isinstance(raw_services, (tuple, list)) or len(raw_services) > 20:
        raise PayloadError("services inválido")
    processes = []
    for item in raw_processes:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PayloadError("proceso inválido")
        processes.append(ProcessInfo(int(_value(item, "pid", 0, 2**31)),
                                     item["name"][:80], int(_value(item, "memory_bytes"))))
    services = []
    for item in raw_services:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("state"), str) or type(item.get("active")) is not bool:
            raise PayloadError("servicio inválido")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,95}", item["name"]):
            raise PayloadError("nombre de servicio inválido")
        services.append(ServiceStatus(item["name"], item["active"], item["state"][:32]))
    return Snapshot(
        hostname=host, timestamp=stamp,
        cpu_percent=_value(data, "cpu_percent", 0, 100),
        cpu_logical_cores=int(_value(data, "cpu_logical_cores", 1, 4096)),
        ram_percent=_value(data, "ram_percent", 0, 100),
        ram_used_bytes=int(_value(data, "ram_used_bytes")),
        ram_total_bytes=int(_value(data, "ram_total_bytes")),
        disk_percent=_value(data, "disk_percent", 0, 100),
        disk_used_bytes=int(_value(data, "disk_used_bytes")),
        disk_total_bytes=int(_value(data, "disk_total_bytes")),
        disk_path=disk_path,
        uptime_seconds=int(_value(data, "uptime_seconds")),
        load_1m=load[0], load_5m=load[1], load_15m=load[2],
        processes_total=int(_value(data, "processes_total", 0, 10_000_000)),
        network_sent_bytes=int(_value(data, "network_sent_bytes")),
        network_received_bytes=int(_value(data, "network_received_bytes")),
        top_processes=tuple(processes), services=tuple(services),
    )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        # No reenviar el token a un dominio diferente por redirección.
        return None


def send_snapshot(snapshot: Snapshot, hub_url: str, token: str) -> None:
    """Publica métricas. Rechaza redirecciones, limita tiempo y no filtra token."""
    if not hub_url or not token:
        raise ValueError("Configura SW_HUB_URL y SW_INGEST_TOKEN en el agente")
    payload = json.dumps(asdict(snapshot), allow_nan=False).encode("utf-8")
    if len(payload) > 30_000:
        raise ValueError("Payload demasiado grande")
    request = Request(
        f"{hub_url}/api/ingest",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    opener = build_opener(_NoRedirect, HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=10) as response:
            if response.status != 202:
                raise OSError("Central no aceptó la muestra")
    except (HTTPError, URLError, TimeoutError, OSError):
        raise OSError("No se pudo entregar la muestra a la central; revisa HTTPS, acceso y token") from None
