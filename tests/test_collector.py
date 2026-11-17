"""Pruebas de captura real en modo solo lectura."""

from dataclasses import asdict

from serverwatch.collector import collect_snapshot
from serverwatch.formatters import format_snapshot, human_bytes


def test_collect_real_snapshot():
    snapshot = collect_snapshot(top_processes=2, cpu_sample_seconds=0.1)
    assert snapshot.hostname
    assert 0 <= snapshot.cpu_percent <= 100
    assert 0 <= snapshot.ram_percent <= 100
    assert 0 <= snapshot.disk_percent <= 100
    assert snapshot.uptime_seconds >= 0
    assert snapshot.processes_total > 0
    assert len(snapshot.top_processes) <= 2
    assert "CPU:" in format_snapshot(snapshot)
    assert isinstance(asdict(snapshot)["top_processes"], tuple)


def test_bytes():
    assert human_bytes(1024) == "1.0 KiB"
    assert human_bytes(1_048_576) == "1.0 MiB"
