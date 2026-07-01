def test_investigate_unknown_alert_returns_404(client):
    resp = client.get("/investigate/does-not-exist/stream")
    assert resp.status_code == 404


def test_investigate_streams_not_implemented_error(client):
    # AgentLoop.run() isn't built yet (see app/agent/loop.py) — the endpoint
    # should still be a real SSE stream, just one that reports that honestly
    # instead of 404ing or 500ing.
    alert = client.post("/alerts/generate", json={"type": "data_exfiltration"}).json()

    with client.stream("GET", f"/investigate/{alert['id']}/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        lines = []
        for line in resp.iter_lines():
            lines.append(line)
            if any(l.startswith("data:") for l in lines):
                break

    body = "\n".join(lines)
    assert "event: error" in body
    assert "not implemented" in body.lower()
