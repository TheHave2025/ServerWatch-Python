"""Validación de telemetría recibida; entradas maliciosas se rechazan."""

from dataclasses import asdict

import pytest

from serverwatch.remote import PayloadError, validate_snapshot


def test_valid_snapshot(snapshot):
    result = validate_snapshot(asdict(snapshot))
    assert result == snapshot


def test_invalid_percent(snapshot):
    data = asdict(snapshot)
    data["cpu_percent"] = 110
    with pytest.raises(PayloadError):
        validate_snapshot(data)


def test_invalid_host(snapshot):
    data = asdict(snapshot)
    data["hostname"] = "../../etc/passwd"
    with pytest.raises(PayloadError):
        validate_snapshot(data)


def test_invalid_nan(snapshot):
    data = asdict(snapshot)
    data["ram_percent"] = float("nan")
    with pytest.raises(PayloadError):
        validate_snapshot(data)


def test_invalid_process(snapshot):
    data = asdict(snapshot)
    data["top_processes"] = [{"pid": -1, "name": "x", "memory_bytes": 4}]
    with pytest.raises(PayloadError):
        validate_snapshot(data)
