from app import ratelimit
from app.ratelimit import _SlidingWindowCounter


def test_sliding_window_counter_blocks_after_max_calls():
    counter = _SlidingWindowCounter(max_calls=2, window_seconds=60)

    assert counter.allow("1.1.1.1") is True
    assert counter.allow("1.1.1.1") is True
    assert counter.allow("1.1.1.1") is False


def test_sliding_window_counter_tracks_keys_independently():
    counter = _SlidingWindowCounter(max_calls=1, window_seconds=60)

    assert counter.allow("1.1.1.1") is True
    assert counter.allow("2.2.2.2") is True
    assert counter.allow("1.1.1.1") is False


def test_generate_endpoint_returns_429_once_per_ip_limit_exceeded(client, monkeypatch):
    monkeypatch.setattr(ratelimit, "_generate_per_ip", _SlidingWindowCounter(max_calls=2, window_seconds=60))

    assert client.post("/alerts/generate", json={}).status_code == 200
    assert client.post("/alerts/generate", json={}).status_code == 200
    resp = client.post("/alerts/generate", json={})

    assert resp.status_code == 429


def test_investigate_endpoint_returns_429_once_per_ip_limit_exceeded(client, monkeypatch):
    # sse_starlette's AppStatus event is bound to the event loop of the first
    # SSE request TestClient makes, so a second live SSE call in the same
    # test trips a spurious "different event loop" error. Instead of making
    # two real requests, pre-consume the only slot directly (as if a prior
    # request already used it — "testclient" is TestClient's fixed host)
    # and assert the next request is rejected.
    limiter = _SlidingWindowCounter(max_calls=1, window_seconds=60)
    limiter.allow("testclient")
    monkeypatch.setattr(ratelimit, "_investigate_per_ip", limiter)

    alert = client.post("/alerts/generate", json={}).json()
    resp = client.get(f"/investigate/{alert['id']}/stream")

    assert resp.status_code == 429


def test_investigate_endpoint_returns_429_once_global_limit_exceeded(client, monkeypatch):
    limiter = _SlidingWindowCounter(max_calls=1, window_seconds=60)
    limiter.allow("*")
    monkeypatch.setattr(ratelimit, "_investigate_global", limiter)

    alert = client.post("/alerts/generate", json={}).json()
    resp = client.get(f"/investigate/{alert['id']}/stream")

    assert resp.status_code == 429
