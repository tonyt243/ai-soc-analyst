"""Live threat-intel clients for `enrich_ip` (AbuseIPDB) and `lookup_cve` (NVD).

Each provider gets its own module-level `TTLCache` (avoid paying for/re-hitting
the same lookup within one demo session) and `RateLimiter` (stay under each
provider's free-tier limits even if several investigations run concurrently).
Both are in-memory, process-lifetime state — consistent with the rest of this
project's "no persistence beyond in-memory/session state" scope (see
app/alerts/store.py for the same pattern applied to alerts).

`_http_get` is factored out purely so tests can monkeypatch one seam instead
of mocking httpx's client/response internals.
"""

import asyncio
import time
from collections import deque
from typing import Any

import httpx

_TIMEOUT_SECONDS = 10.0


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl_seconds, value)


class RateLimiter:
    """Sliding-window limiter: blocks until fewer than `max_calls` have gone out
    in the trailing `window_seconds`, so a provider's free-tier limit is never
    exceeded even under concurrent investigations."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._call_times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._evict_expired()
            if len(self._call_times) >= self._max_calls:
                sleep_for = self._window_seconds - (time.monotonic() - self._call_times[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                self._evict_expired()
            self._call_times.append(time.monotonic())

    def _evict_expired(self) -> None:
        now = time.monotonic()
        while self._call_times and now - self._call_times[0] > self._window_seconds:
            self._call_times.popleft()


async def _http_get(url: str, *, params: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response


# AbuseIPDB free tier: 1000 checks/day, no documented per-second cap — stay
# conservative so a burst of investigations can't blow through the daily quota.
_ABUSEIPDB_CACHE = TTLCache(ttl_seconds=3600)
_ABUSEIPDB_LIMITER = RateLimiter(max_calls=1, window_seconds=1.5)

# NVD: 5 requests/30s unauthenticated, 50/30s with an API key.
_NVD_CACHE = TTLCache(ttl_seconds=86400)
_NVD_LIMITER = RateLimiter(max_calls=5, window_seconds=30)


async def abuseipdb_check(ip: str, api_key: str) -> dict[str, Any]:
    cached = _ABUSEIPDB_CACHE.get(ip)
    if cached is not None:
        return cached

    await _ABUSEIPDB_LIMITER.acquire()
    response = await _http_get(
        "https://api.abuseipdb.com/api/v2/check",
        params={"ipAddress": ip, "maxAgeInDays": 90},
        headers={"Key": api_key, "Accept": "application/json"},
    )
    data = response.json()["data"]
    result = {
        "ip": ip,
        "classification": "external",
        "country": data.get("countryCode"),
        "asn_org": data.get("isp"),
        "reputation_score": data.get("abuseConfidenceScore"),
        "known_malicious": (data.get("abuseConfidenceScore") or 0) >= 50,
        "total_reports": data.get("totalReports"),
        "notes": f"AbuseIPDB: {data.get('totalReports', 0)} report(s), "
        f"last reported {data.get('lastReportedAt') or 'never'}.",
    }
    _ABUSEIPDB_CACHE.set(ip, result)
    return result


async def nvd_lookup(cve_id: str, api_key: str) -> dict[str, Any]:
    cached = _NVD_CACHE.get(cve_id)
    if cached is not None:
        return cached

    await _NVD_LIMITER.acquire()
    headers = {"apiKey": api_key} if api_key else {}
    response = await _http_get(
        "https://services.nvd.nist.gov/rest/json/cves/2.0",
        params={"cveId": cve_id},
        headers=headers,
    )
    vulnerabilities = response.json().get("vulnerabilities", [])
    if not vulnerabilities:
        result = {
            "cve_id": cve_id,
            "description": "No record found for this CVE in NVD.",
            "cvss_score": None,
            "actively_exploited": None,
        }
    else:
        cve = vulnerabilities[0]["cve"]
        description = next(
            (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
            "No English-language description available.",
        )
        cvss_score = None
        for metric_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric = cve.get("metrics", {}).get(metric_key)
            if metric:
                cvss_score = metric[0]["cvssData"]["baseScore"]
                break
        result = {
            "cve_id": cve_id,
            "description": description,
            "cvss_score": cvss_score,
            # NVD surfaces CISA's Known Exploited Vulnerabilities catalog as
            # this field being present, rather than a plain boolean flag.
            "actively_exploited": "cisaExploitAdd" in cve,
        }
    _NVD_CACHE.set(cve_id, result)
    return result
