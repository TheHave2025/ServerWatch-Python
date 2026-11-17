"""Persistencia SQLite. Las escrituras son transacciones cortas, con WAL.

No guarda tokens ni direcciones IP. Solo datos agregados de sistemas y eventos.
"""

import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from .models import AlertEvent, Snapshot


class Database:
    def __init__(self, filename: str):
        self.filename = filename
        Path(filename).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    received_at INTEGER NOT NULL,
                    cpu REAL NOT NULL,
                    ram REAL NOT NULL,
                    disk REAL NOT NULL,
                    snapshot_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS samples_server_time
                    ON samples(server_id, received_at DESC);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    received_at INTEGER NOT NULL,
                    metric TEXT NOT NULL,
                    status TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_time ON events(received_at DESC);
            """)

    def _connect(self):
        db = sqlite3.connect(self.filename, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def save(self, snapshot: Snapshot, events: list[AlertEvent] = None):
        now = int(time.time())
        with self._connect() as db:
            db.execute(
                "INSERT INTO samples(server_id,received_at,cpu,ram,disk,snapshot_json) "
                "VALUES (?,?,?,?,?,?)",
                (snapshot.hostname, now, snapshot.cpu_percent, snapshot.ram_percent,
                 snapshot.disk_percent, json.dumps(asdict(snapshot), ensure_ascii=False)),
            )
            db.executemany(
                "INSERT INTO events(server_id,received_at,metric,status,value,threshold) "
                "VALUES (?,?,?,?,?,?)",
                [(e.hostname, now, e.metric, e.status, e.value, e.threshold)
                 for e in (events or [])],
            )

    def servers(self, offline_after: int) -> list[dict]:
        now = int(time.time())
        with self._connect() as db:
            rows = db.execute("""
                SELECT s.server_id, s.received_at, s.snapshot_json
                FROM samples s
                WHERE s.id=(SELECT MAX(t.id) FROM samples t WHERE t.server_id=s.server_id)
                ORDER BY s.server_id ASC
            """).fetchall()
        return [{"id": row["server_id"], "last_seen": row["received_at"],
                 "online": now - row["received_at"] <= offline_after,
                 "snapshot": json.loads(row["snapshot_json"])} for row in rows]

    def history(self, server_id: str, limit: int = 120) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("""
                SELECT received_at, cpu, ram, disk FROM samples
                WHERE server_id=? ORDER BY id DESC LIMIT ?
            """, (server_id, min(max(limit, 1), 500))).fetchall()
        return [dict(row) for row in reversed(rows)]

    def events(self, limit: int = 30) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("""
                SELECT server_id, received_at, metric, status, value, threshold
                FROM events ORDER BY id DESC LIMIT ?
            """, (min(max(limit, 1), 100),)).fetchall()
        return [dict(row) for row in rows]

    def prune(self, days: int) -> tuple[int, int]:
        cutoff = int(time.time()) - days * 86400
        with self._connect() as db:
            a = db.execute("DELETE FROM samples WHERE received_at < ?", (cutoff,)).rowcount
            b = db.execute("DELETE FROM events WHERE received_at < ?", (cutoff,)).rowcount
        return (a, b)
