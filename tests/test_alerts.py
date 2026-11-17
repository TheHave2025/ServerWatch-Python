"""Las alertas se emiten en transiciones y con recordatorios limitados."""

from serverwatch.alerts import AlertTracker


def test_trigger_reminder_recovery(settings, modified_snapshot):
    tracker = AlertTracker(settings)
    high = modified_snapshot(cpu_percent=93)
    assert [(e.metric, e.status) for e in tracker.evaluate(high, now=100)] == [
        ("cpu", "triggered")
    ]
    assert tracker.evaluate(high, now=399) == []
    assert [(e.metric, e.status) for e in tracker.evaluate(high, now=400)] == [
        ("cpu", "reminder")
    ]

    # Histéresis: 78% está por debajo de 80, pero aún no baja a 75.
    assert tracker.evaluate(modified_snapshot(cpu_percent=78), now=401) == []
    assert [(e.metric, e.status) for e in tracker.evaluate(modified_snapshot(cpu_percent=75), now=402)] == [
        ("cpu", "recovered")
    ]
    assert tracker.evaluate(modified_snapshot(cpu_percent=75), now=403) == []
    assert [(e.metric, e.status) for e in tracker.evaluate(high, now=404)] == [
        ("cpu", "triggered")
    ]


def test_multiple_thresholds(settings, modified_snapshot):
    tracker = AlertTracker(settings)
    sample = modified_snapshot(cpu_percent=80, ram_percent=89, disk_percent=92)
    assert {e.metric for e in tracker.evaluate(sample, now=0)} == {"cpu", "ram", "disk"}


def test_normal_state_no_event(settings, snapshot):
    assert AlertTracker(settings).evaluate(snapshot, now=0) == []


def test_zero_cooldown_allows_reminder(settings, modified_snapshot):
    from dataclasses import replace

    tracker = AlertTracker(replace(settings, cooldown=0))
    sample = modified_snapshot(cpu_percent=90)
    assert tracker.evaluate(sample, now=1)[0].status == "triggered"
    assert tracker.evaluate(sample, now=1)[0].status == "reminder"
