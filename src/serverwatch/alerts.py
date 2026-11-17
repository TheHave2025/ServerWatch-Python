"""Motor de alertas con cooldown y margen de recuperación (histéresis)."""

import time

from .config import Config
from .models import AlertEvent, AlertMetric, Snapshot


class AlertTracker:
    """Recuerda umbrales activos durante la vida del proceso.

    Transiciones:
    * Inactivo -> por encima del umbral: alerta nueva.
    * Activo -> alto durante cooldown: recordatorio.
    * Activo -> valor <= umbral - margen: recuperación.

    Se usa tiempo monótono para impedir efectos de ajustes del reloj.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._active: set[AlertMetric] = set()
        self._last_sent: dict[AlertMetric, float] = {}
        self._service_active: set[str] = set()

    def evaluate(self, snapshot: Snapshot, now: float | None = None) -> list[AlertEvent]:
        current_time = time.monotonic() if now is None else now
        values: dict[AlertMetric, tuple[float, float]] = {
            "cpu": (snapshot.cpu_percent, self._config.cpu_threshold),
            "ram": (snapshot.ram_percent, self._config.ram_threshold),
            "disk": (snapshot.disk_percent, self._config.disk_threshold),
        }
        events: list[AlertEvent] = []

        for metric, (value, threshold) in values.items():
            status = None
            if metric not in self._active and value >= threshold:
                self._active.add(metric)
                self._last_sent[metric] = current_time
                status = "triggered"
            elif metric in self._active and value <= threshold - self._config.recovery_margin:
                self._active.remove(metric)
                self._last_sent.pop(metric, None)
                status = "recovered"
            elif (
                metric in self._active
                and value >= threshold
                and current_time - self._last_sent[metric] >= self._config.cooldown
            ):
                self._last_sent[metric] = current_time
                status = "reminder"

            if status is not None:
                events.append(
                    AlertEvent(
                        metric=metric,
                        status=status,
                        value=value,
                        threshold=threshold,
                        hostname=snapshot.hostname,
                        timestamp=snapshot.timestamp,
                    )
                )
        # Los servicios que no están activos disparan una alerta y recuperan al volver.
        # Evita el aviso espurio al cambiar a un servicio antes desconocido.
        for service in snapshot.services:
            metric = f"service:{service.name}"
            was_active = metric in self._service_active
            is_down = not service.active
            status = None
            if is_down and not was_active:
                self._service_active.add(metric)
                self._last_sent[metric] = current_time
                status = "triggered"
            elif not is_down and was_active:
                self._service_active.remove(metric)
                self._last_sent.pop(metric, None)
                status = "recovered"
            elif is_down and was_active and current_time - self._last_sent.get(metric, current_time) >= self._config.cooldown:
                self._last_sent[metric] = current_time
                status = "reminder"
            if status is not None:
                events.append(AlertEvent(metric=metric, status=status, value=0 if is_down else 1,
                                         threshold=1, hostname=snapshot.hostname, timestamp=snapshot.timestamp))
        return events
