"""Lee y valida configuración exclusivamente desde variables de entorno.

Se admite un archivo .env en el directorio de trabajo. Las variables ya
presentes en el entorno tienen preferencia sobre las escritas en .env.
"""

import os
import re
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(ValueError):
    """La configuración no es válida para iniciar el monitor."""


def _number(name: str, default: float, lower: float, upper: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser numérico") from exc
    if not lower <= value <= upper:
        raise ConfigError(f"{name} debe estar entre {lower:g} y {upper:g}")
    return value


def _integer(name: str, default: int, lower: int, upper: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser entero") from exc
    if not lower <= value <= upper:
        raise ConfigError(f"{name} debe estar entre {lower} y {upper}")
    return value


@dataclass(frozen=True)
class Config:
    """Ajustes tipados, independientes de la interfaz de comandos."""

    interval: int
    cpu_threshold: float
    ram_threshold: float
    disk_threshold: float
    disk_path: str
    cooldown: int
    recovery_margin: float
    top_processes: int
    cpu_sample_seconds: float
    telegram_token: str
    telegram_chat_id: str
    database: str = "./serverwatch.sqlite3"
    retention_days: int = 30
    offline_after: int = 120
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8787
    dashboard_password: str = ""
    ingest_token: str = ""
    hub_url: str = ""
    node_name: str = ""
    services: tuple[str, ...] = ()

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id)

    @classmethod
    def from_env(cls) -> "Config":
        """Carga .env del cwd y valida todos los parámetros conocidos."""
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
        token = os.getenv("SW_TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("SW_TELEGRAM_CHAT_ID", "").strip()
        if bool(token) != bool(chat_id):
            raise ConfigError(
                "Configura ambos SW_TELEGRAM_BOT_TOKEN y SW_TELEGRAM_CHAT_ID, "
                "o deja ambos vacíos"
            )
        disk_path = os.getenv("SW_DISK_PATH", "/").strip()
        if not disk_path:
            raise ConfigError("SW_DISK_PATH no puede estar vacío")
        if not Path(disk_path).is_dir():
            raise ConfigError("SW_DISK_PATH debe ser un directorio existente")
        service_names = tuple(x.strip() for x in os.getenv("SW_SERVICES", "").split(",") if x.strip())
        if len(service_names) > 20 or any(
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,95}", x)
            for x in service_names
        ):
            raise ConfigError("SW_SERVICES debe listar hasta 20 nombres systemd válidos")
        host = os.getenv("SW_DASHBOARD_HOST", "127.0.0.1").strip()
        if host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0", "::"):
            raise ConfigError("SW_DASHBOARD_HOST debe ser local o una interfaz permitida")
        password = os.getenv("SW_DASHBOARD_PASSWORD", "").strip()
        if host in ("0.0.0.0", "::") and len(password) < 16:
            raise ConfigError("Al escuchar en todas las interfaces, SW_DASHBOARD_PASSWORD debe tener al menos 16 caracteres")
        url = os.getenv("SW_HUB_URL", "").strip().rstrip("/")
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
                raise ConfigError("SW_HUB_URL debe ser una URL de base sin usuario ni rutas")
            if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
                raise ConfigError("SW_HUB_URL remoto debe usar HTTPS")
        if 0 < len(os.getenv("SW_INGEST_TOKEN", "").strip()) < 32:
            raise ConfigError("SW_INGEST_TOKEN debe tener al menos 32 caracteres")
        database = os.getenv("SW_DATABASE", "./serverwatch.sqlite3").strip()
        if not database:
            raise ConfigError("SW_DATABASE no puede estar vacío")
        node_name = os.getenv("SW_NODE_NAME", "").strip()
        if node_name and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", node_name):
            raise ConfigError("SW_NODE_NAME solo admite letras, números, puntos, guiones y _")
        return cls(
            interval=_integer("SW_INTERVAL", 30, 1, 86400),
            cpu_threshold=_number("SW_CPU_THRESHOLD", 90, 0, 100),
            ram_threshold=_number("SW_RAM_THRESHOLD", 90, 0, 100),
            disk_threshold=_number("SW_DISK_THRESHOLD", 90, 0, 100),
            disk_path=disk_path,
            cooldown=_integer("SW_ALERT_COOLDOWN", 1800, 0, 604800),
            recovery_margin=_number("SW_RECOVERY_MARGIN", 5, 0, 20),
            top_processes=_integer("SW_TOP_PROCESSES", 5, 0, 30),
            cpu_sample_seconds=_number("SW_CPU_SAMPLE_SECONDS", 0.3, 0.1, 5),
            telegram_token=token,
            telegram_chat_id=chat_id,
            database=database,
            retention_days=_integer("SW_RETENTION_DAYS", 30, 1, 3650),
            offline_after=_integer("SW_OFFLINE_AFTER", 120, 10, 86400),
            dashboard_host=host,
            dashboard_port=_integer("SW_DASHBOARD_PORT", 8787, 1, 65535),
            dashboard_password=password,
            ingest_token=os.getenv("SW_INGEST_TOKEN", "").strip(),
            hub_url=url,
            node_name=node_name,
            services=service_names,
        )

    def public_settings(self) -> dict[str, str | int | float | bool]:
        """Vista segura: nunca incluye el token ni el identificador del chat."""
        return {
            "interval_seconds": self.interval,
            "cpu_threshold_percent": self.cpu_threshold,
            "ram_threshold_percent": self.ram_threshold,
            "disk_threshold_percent": self.disk_threshold,
            "disk_path": self.disk_path,
            "cooldown_seconds": self.cooldown,
            "recovery_margin_percent": self.recovery_margin,
            "top_processes": self.top_processes,
            "cpu_sample_seconds": self.cpu_sample_seconds,
            "telegram_enabled": self.telegram_enabled,
            "database": self.database,
            "retention_days": self.retention_days,
            "offline_after": self.offline_after,
            "dashboard_host": self.dashboard_host,
            "dashboard_port": self.dashboard_port,
            "dashboard_password_enabled": bool(self.dashboard_password),
            "ingest_enabled": bool(self.ingest_token),
            "hub_url": self.hub_url,
            "node_name": self.node_name,
            "services": list(self.services),
        }
