import pytest

from app.agent.loop import get_agent_loop
from app.main import app
from app.schemas.events import TextDelta, VerdictReady


class _FakeAgentLoop:
    """Stands in for the real AgentLoop so router tests never touch the
    real Anthropic API — AgentLoop's own behavior is covered in
    test_agent_loop.py."""

    async def run(self, alert):
        yield TextDelta(text=f"Investigating {alert.title}")
        yield VerdictReady(verdict={"severity": "high", "mitre_technique": "T1110"})


@pytest.fixture(autouse=True)
def _override_agent_loop():
    app.dependency_overrides[get_agent_loop] = lambda: _FakeAgentLoop()
    yield
    app.dependency_overrides.pop(get_agent_loop, None)


def test_investigate_unknown_alert_returns_404(client):
    resp = client.get("/investigate/does-not-exist/stream")
    assert resp.status_code == 404


def test_investigate_streams_agent_events(client):
    alert = client.post("/alerts/generate", json={"type": "data_exfiltration"}).json()

    with client.stream("GET", f"/investigate/{alert['id']}/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        lines = list(resp.iter_lines())

    body = "\n".join(lines)
    assert "event: text_delta" in body
    assert "event: verdict_ready" in body
    assert alert["title"] in body
