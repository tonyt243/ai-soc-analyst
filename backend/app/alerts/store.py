"""In-memory alert store.

v1 scope is explicitly "no persistence beyond in-memory/session state" (see
CLAUDE.md) — this dict is it. Alerts vanish on server restart; that's fine
for a demo where you generate an alert and immediately investigate it.
"""

from app.alerts.models import Alert

_alerts: dict[str, Alert] = {}


def save(alert: Alert) -> Alert:
    _alerts[alert.id] = alert
    return alert


def get(alert_id: str) -> Alert | None:
    return _alerts.get(alert_id)


def list_all() -> list[Alert]:
    return sorted(_alerts.values(), key=lambda a: a.generated_at, reverse=True)


def reset() -> None:
    """Test-only: clear the store so tests don't leak alerts into each other."""
    _alerts.clear()
