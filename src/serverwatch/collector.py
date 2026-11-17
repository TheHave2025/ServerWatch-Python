"""Recolección local y de solo lectura con psutil."""

import os
import socket
import time
from datetime import datetime

import psutil

from .models import ProcessInfo, ServiceStatus, Snapshot
import re
import subprocess


def _load_average() -> tuple[float | None, float | None, float | None]:
    try:
        return tuple(round(x, 2) for x in os.getloadavg())
    except (AttributeError, OSError):
        return (None, None, None)


def _biggest_processes(limit: int) -> tuple[ProcessInfo, ...]:
    if limit == 0:
        return ()
    found: list[ProcessInfo] = []
    # Algunos procesos requieren privilegios; se omiten sin detener el servicio.
    for process in psutil.process_iter(["pid", "name", "memory_info"], ad_value=None):
        try:
            info = process.info
            memory_info = info.get("memory_info")
            if memory_info is None:
                continue
            found.append(
                ProcessInfo(
                    pid=int(info["pid"]),
                    name=str(info.get("name") or "desconocido")[:80],
                    memory_bytes=int(memory_info.rss),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError):
            continue
    return tuple(sorted(found, key=lambda p: p.memory_bytes, reverse=True)[:limit])


_SERVICE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,95}$")


def _service_states(names: tuple[str, ...]) -> tuple[ServiceStatus, ...]:
    """Comprueba servicios sin shell ni permisos root. Limita cada llamada a 2 segundos."""
    statuses = []
    for name in names[:20]:
        if not _SERVICE_RE.fullmatch(name):
            continue
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "--", name],
                capture_output=True, text=True, timeout=2, check=False,
            )
            state = result.stdout.strip()[:32] or "unknown"
            active = result.returncode == 0 and state == "active"
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            state, active = "unknown", False
        statuses.append(ServiceStatus(name=name, active=active, state=state))
    return tuple(statuses)


def collect_snapshot(
    disk_path: str = "/", top_processes: int = 5, cpu_sample_seconds: float = 0.3,
    services: tuple[str, ...] = (),
) -> Snapshot:
    """Lee CPU, RAM, disco, uptime, red y procesos principales.

    No ejecuta shell, no necesita root y no hace llamadas de red. El porcentaje
    de CPU se mide durante `cpu_sample_seconds`, por lo que la toma tarda ese
    tiempo aproximadamente.
    """
    cpu = psutil.cpu_percent(interval=cpu_sample_seconds)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_path)
    network = psutil.net_io_counters()
    load_1m, load_5m, load_15m = _load_average()
    return Snapshot(
        hostname=socket.gethostname(),
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        cpu_percent=round(cpu, 1),
        cpu_logical_cores=psutil.cpu_count(logical=True) or 1,
        ram_percent=round(ram.percent, 1),
        ram_used_bytes=int(ram.total - ram.available),
        ram_total_bytes=int(ram.total),
        disk_percent=round(disk.percent, 1),
        disk_used_bytes=int(disk.used),
        disk_total_bytes=int(disk.total),
        disk_path=disk_path,
        uptime_seconds=max(0, int(time.time() - psutil.boot_time())),
        load_1m=load_1m,
        load_5m=load_5m,
        load_15m=load_15m,
        processes_total=len(psutil.pids()),
        network_sent_bytes=int(network.bytes_sent) if network else 0,
        network_received_bytes=int(network.bytes_recv) if network else 0,
        top_processes=_biggest_processes(top_processes),
        services=_service_states(services),
    )
