"""Fixtures de pruebas sin depender del servidor, ni usar Telegram real."""

from dataclasses import replace

import pytest

from serverwatch.config import Config
from serverwatch.models import Snapshot


@pytest.fixture
def settings() -> Config:
    return Config(
        interval=30,
        cpu_threshold=80,
        ram_threshold=85,
        disk_threshold=90,
        disk_path="/",
        cooldown=300,
        recovery_margin=5,
        top_processes=5,
        cpu_sample_seconds=0.1,
        telegram_token="",
        telegram_chat_id="",
    )


@pytest.fixture
def snapshot() -> Snapshot:
    return Snapshot(
        hostname="test-ubuntu",
        timestamp="2026-11-17T10:00:00-06:00",
        cpu_percent=10.0,
        cpu_logical_cores=4,
        ram_percent=20.0,
        ram_used_bytes=2_000,
        ram_total_bytes=10_000,
        disk_percent=30.0,
        disk_used_bytes=3_000,
        disk_total_bytes=10_000,
        disk_path="/",
        uptime_seconds=7200,
        load_1m=0.2,
        load_5m=0.4,
        load_15m=0.5,
        processes_total=100,
        network_sent_bytes=100_000,
        network_received_bytes=200_000,
        top_processes=(),
    )


@pytest.fixture
def modified_snapshot(snapshot):
    return lambda **kwargs: replace(snapshot, **kwargs)
