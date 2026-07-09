"""In-memory per-IP + global rate limiting for public-facing endpoints.

This app is meant to be deployed with a public demo link (see CLAUDE.md §
v2 scope, deploy). `/investigate/{id}/stream` calls the real, paid Claude
API (`opus-4-8`, up to `MAX_TURNS` turns) on every hit — an unauthenticated
public endpoint with no cap is a real cost risk, not just a traffic-shaping
nicety. Two layers apply to it: a per-IP window (stops one visitor from
looping the button) and a global window (a circuit breaker bounding total
spend even if requests come from many different/spoofed IPs). Alert
generation is free (synthetic data only) but still gets a looser per-IP cap
to stop the in-memory alert store from being flooded.

In-memory only, consistent with the rest of this project's persistence
scope (see `app/alerts/store.py`) — resets on restart, which is fine for a
demo. Rejects over the limit with a 429 rather than queuing (unlike
`app/agent/enrichment.py`'s `RateLimiter`, which delays outbound calls to a
third party) — the point here is to refuse extra Claude API calls outright.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_PER_IP_MAX_INVESTIGATIONS = 5
_PER_IP_INVESTIGATE_WINDOW_SECONDS = 600  # 10 minutes

_GLOBAL_MAX_INVESTIGATIONS = 100
_GLOBAL_INVESTIGATE_WINDOW_SECONDS = 86400  # 1 day — bounds worst-case daily spend

_PER_IP_MAX_GENERATIONS = 30
_PER_IP_GENERATE_WINDOW_SECONDS = 600


class _SlidingWindowCounter:
    """Tracks call timestamps per key. `allow(key)` checks-and-records in one
    step, rejecting once `max_calls` have landed in the trailing window."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        calls = self._calls[key]
        while calls and now - calls[0] > self.window_seconds:
            calls.popleft()
        if len(calls) >= self.max_calls:
            return False
        calls.append(now)
        return True

    def reset(self) -> None:
        self._calls.clear()


_investigate_per_ip = _SlidingWindowCounter(_PER_IP_MAX_INVESTIGATIONS, _PER_IP_INVESTIGATE_WINDOW_SECONDS)
_investigate_global = _SlidingWindowCounter(_GLOBAL_MAX_INVESTIGATIONS, _GLOBAL_INVESTIGATE_WINDOW_SECONDS)
_generate_per_ip = _SlidingWindowCounter(_PER_IP_MAX_GENERATIONS, _PER_IP_GENERATE_WINDOW_SECONDS)


def _client_ip(request: Request) -> str:
    # Railway (and most PaaS) sit behind a proxy — the real client IP is the
    # first hop of X-Forwarded-For, not request.client.host (the proxy).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_investigate_limit(request: Request) -> None:
    ip = _client_ip(request)
    if not _investigate_per_ip.allow(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many investigations from this IP — try again in a few minutes.",
        )
    if not _investigate_global.allow("*"):
        raise HTTPException(
            status_code=429,
            detail="This demo has hit its investigation limit for today — try again later.",
        )


def enforce_generate_limit(request: Request) -> None:
    ip = _client_ip(request)
    if not _generate_per_ip.allow(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many alerts generated from this IP — try again in a few minutes.",
        )


def reset_all() -> None:
    """Test-only: clear all counters so tests don't leak rate-limit state
    into each other (mirrors app/alerts/store.py's reset())."""
    _investigate_per_ip.reset()
    _investigate_global.reset()
    _generate_per_ip.reset()
