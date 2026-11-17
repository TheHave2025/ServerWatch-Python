"""Alertas por servicios systemd, con recordatorios y recuperación."""

from dataclasses import replace

from serverwatch.alerts import AlertTracker
from serverwatch.models import ServiceStatus


def test_service_down_reminder_recovered(settings, snapshot):
    tracker = AlertTracker(settings)
    down = replace(snapshot, services=(ServiceStatus("nginx", False, "inactive"),))
    first = tracker.evaluate(down, now=0)
    assert any(e.metric == "service:nginx" and e.status == "triggered" for e in first)
    assert tracker.evaluate(down, now=1) == []
    reminder = tracker.evaluate(down, now=301)
    assert any(e.status == "reminder" and e.metric == "service:nginx" for e in reminder)
    up = replace(snapshot, services=(ServiceStatus("nginx", True, "active"),))
    recovery = tracker.evaluate(up, now=302)
    assert any(e.status == "recovered" and e.metric == "service:nginx" for e in recovery)
