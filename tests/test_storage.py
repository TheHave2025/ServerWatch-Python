"""Contrato SQLite: persistencia, historial, eventos y retención."""

from dataclasses import replace

from serverwatch.models import AlertEvent
from serverwatch.storage import Database


def test_samples_and_events(tmp_path, snapshot):
    db = Database(str(tmp_path / "test.sqlite3"))
    alert = AlertEvent("cpu", "triggered", 95.0, 90.0, snapshot.hostname, snapshot.timestamp)
    db.save(snapshot, [alert])
    db.save(replace(snapshot, cpu_percent=35.0))
    servers = db.servers(120)
    assert len(servers) == 1
    assert servers[0]["id"] == "test-ubuntu"
    assert servers[0]["online"] is True
    assert servers[0]["snapshot"]["cpu_percent"] == 35.0
    assert [x["cpu"] for x in db.history(snapshot.hostname)] == [10.0, 35.0]
    assert db.events()[0]["status"] == "triggered"
    assert db.prune(30) == (0, 0)


def test_server_ids_isolated(tmp_path, snapshot):
    db = Database(str(tmp_path / "x.sqlite3"))
    db.save(snapshot)
    db.save(replace(snapshot, hostname="remote-2"))
    assert len(db.servers(120)) == 2
    assert len(db.history("remote-2")) == 1
    assert not db.history("does-not-exist")
