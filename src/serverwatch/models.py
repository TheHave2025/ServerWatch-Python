"""Modelos de datos explícitos para métricas y eventos de alerta."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ProcessInfo:
    """Proceso destacado por memoria residente (RSS)."""

    pid: int
    name: str
    memory_bytes: int


@dataclass(frozen=True)
class ServiceStatus:
    """Estado de un servicio local consultado de forma segura con systemctl."""

    name: str
    active: bool
    state: str


@dataclass(frozen=True)
class Snapshot:
    """Instantánea del estado del servidor.

    Los valores de uso son porcentajes 0-100. Los tamaños están en bytes;
    el timestamp es ISO-8601 con zona horaria para facilitar correlación.
    """

    hostname: str
    timestamp: str
    cpu_percent: float
    cpu_logical_cores: int
    ram_percent: float
    ram_used_bytes: int
    ram_total_bytes: int
    disk_percent: float
    disk_used_bytes: int
    disk_total_bytes: int
    disk_path: str
    uptime_seconds: int
    load_1m: float | None
    load_5m: float | None
    load_15m: float | None
    processes_total: int
    network_sent_bytes: int
    network_received_bytes: int
    top_processes: tuple[ProcessInfo, ...]
    services: tuple[ServiceStatus, ...] = ()


AlertMetric = str  # CPU, RAM, disco o service:<nombre>
AlertStatus = Literal["triggered", "reminder", "recovered"]


@dataclass(frozen=True)
class AlertEvent:
    """Cambio de estado o recordatorio de una alerta."""

    metric: AlertMetric
    status: AlertStatus
    value: float
    threshold: float
    hostname: str
    timestamp: str
