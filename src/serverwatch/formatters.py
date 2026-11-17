"""Representación legible de métricas para terminal y registros."""

from .models import AlertEvent, Snapshot


def human_bytes(value: int) -> str:
    size = float(value)
    for suffix in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(size) < 1024 or suffix == "TiB":
            return f"{size:.1f} {suffix}"
        size /= 1024
    return f"{size:.1f} TiB"


def human_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m"


def format_snapshot(snapshot: Snapshot) -> str:
    processes = "\n".join(
        f"  - {item.name} (PID {item.pid}): {human_bytes(item.memory_bytes)}"
        for item in snapshot.top_processes
    ) or "  (sin procesos visibles)"
    loads = (
        f"{snapshot.load_1m:.2f}, {snapshot.load_5m:.2f}, {snapshot.load_15m:.2f}"
        if snapshot.load_1m is not None
        and snapshot.load_5m is not None
        and snapshot.load_15m is not None
        else "no disponible"
    )
    return (
        f"🖥️  {snapshot.hostname} | {snapshot.timestamp}\n"
        f"CPU:      {snapshot.cpu_percent:.1f}% ({snapshot.cpu_logical_cores} hilos)\n"
        f"RAM:      {snapshot.ram_percent:.1f}% "
        f"({human_bytes(snapshot.ram_used_bytes)} / "
        f"{human_bytes(snapshot.ram_total_bytes)})\n"
        f"Disco:    {snapshot.disk_percent:.1f}% en {snapshot.disk_path} "
        f"({human_bytes(snapshot.disk_used_bytes)} / "
        f"{human_bytes(snapshot.disk_total_bytes)})\n"
        f"Uptime:   {human_uptime(snapshot.uptime_seconds)}\n"
        f"Carga:    {loads} (1, 5, 15 min)\n"
        f"Procesos: {snapshot.processes_total}\n"
        f"Red:      ↑ {human_bytes(snapshot.network_sent_bytes)} | "
        f"↓ {human_bytes(snapshot.network_received_bytes)} (acumulados)\n"
        f"Top RAM:\n{processes}\n"
        f"Servicios: " + (", ".join(f"{x.name}={'OK' if x.active else x.state}"
                                       for x in snapshot.services) or "no configurados")
    )


def format_event(event: AlertEvent) -> str:
    if event.metric.startswith("service:"):
        names = {"triggered": "INACTIVO", "reminder": "SIGUE INACTIVO", "recovered": "ACTIVO"}
        return f"[SERVICIO {names[event.status]}] {event.hostname} | {event.metric[8:]}"
    labels = {"triggered": "ALERTA", "reminder": "RECORDATORIO", "recovered": "RECUPERADO"}
    return (
        f"[{labels[event.status]}] {event.hostname} | {event.metric.upper()} "
        f"{event.value:.1f}% (umbral {event.threshold:.1f}%)"
    )
