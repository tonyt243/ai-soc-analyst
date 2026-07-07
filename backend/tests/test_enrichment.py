"""Tests for app/agent/enrichment.py — TTLCache, RateLimiter, and the
AbuseIPDB/NVD client functions. `_http_get` is monkeypatched so these never
touch the network or need real API keys."""

import asyncio

import httpx
import pytest

from app.agent import enrichment
from app.agent.enrichment import RateLimiter, TTLCache


def _fake_response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.test"))


class TestTTLCache:
    def test_returns_none_when_missing(self):
        cache = TTLCache(ttl_seconds=60)
        assert cache.get("missing") is None

    def test_returns_cached_value_within_ttl(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", {"value": 1})
        assert cache.get("key") == {"value": 1}

    def test_expires_after_ttl(self, monkeypatch):
        cache = TTLCache(ttl_seconds=10)
        clock = [1000.0]
        monkeypatch.setattr(enrichment.time, "monotonic", lambda: clock[0])

        cache.set("key", "value")
        clock[0] += 11
        assert cache.get("key") is None


class TestRateLimiter:
    @pytest.mark.anyio
    async def test_does_not_sleep_under_the_limit(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(asyncio, "sleep", lambda seconds: sleep_calls.append(seconds))
        limiter = RateLimiter(max_calls=2, window_seconds=30)

        await limiter.acquire()
        await limiter.acquire()

        assert sleep_calls == []

    @pytest.mark.anyio
    async def test_sleeps_once_the_window_is_full(self, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(enrichment.time, "monotonic", lambda: clock[0])

        async def fake_sleep(seconds: float) -> None:
            clock[0] += seconds

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        limiter = RateLimiter(max_calls=1, window_seconds=30)

        await limiter.acquire()  # consumes the only slot at t=0
        await limiter.acquire()  # must wait ~30s for the window to clear

        assert clock[0] == pytest.approx(30.0)


class TestAbuseIPDBCheck:
    @pytest.mark.anyio
    async def test_maps_response_fields(self, monkeypatch):
        enrichment._ABUSEIPDB_CACHE._store.clear()

        async def fake_get(url, *, params, headers):
            assert params["ipAddress"] == "1.2.3.4"
            assert headers["Key"] == "test-key"
            return _fake_response(
                {
                    "data": {
                        "countryCode": "RU",
                        "isp": "Example ISP",
                        "abuseConfidenceScore": 87,
                        "totalReports": 12,
                        "lastReportedAt": "2026-01-01T00:00:00Z",
                    }
                }
            )

        monkeypatch.setattr(enrichment, "_http_get", fake_get)

        result = await enrichment.abuseipdb_check("1.2.3.4", "test-key")

        assert result["country"] == "RU"
        assert result["reputation_score"] == 87
        assert result["known_malicious"] is True

    @pytest.mark.anyio
    async def test_caches_repeat_lookups(self, monkeypatch):
        enrichment._ABUSEIPDB_CACHE._store.clear()
        call_count = 0

        async def fake_get(url, *, params, headers):
            nonlocal call_count
            call_count += 1
            return _fake_response({"data": {"abuseConfidenceScore": 10}})

        monkeypatch.setattr(enrichment, "_http_get", fake_get)

        await enrichment.abuseipdb_check("5.6.7.8", "test-key")
        await enrichment.abuseipdb_check("5.6.7.8", "test-key")

        assert call_count == 1


class TestNvdLookup:
    @pytest.mark.anyio
    async def test_extracts_cvss_and_kev_status(self, monkeypatch):
        enrichment._NVD_CACHE._store.clear()

        async def fake_get(url, *, params, headers):
            assert params["cveId"] == "CVE-2021-44228"
            return _fake_response(
                {
                    "vulnerabilities": [
                        {
                            "cve": {
                                "descriptions": [{"lang": "en", "value": "Log4Shell"}],
                                "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 10.0}}]},
                                "cisaExploitAdd": "2021-12-10",
                            }
                        }
                    ]
                }
            )

        monkeypatch.setattr(enrichment, "_http_get", fake_get)

        result = await enrichment.nvd_lookup("CVE-2021-44228", "")

        assert result["description"] == "Log4Shell"
        assert result["cvss_score"] == 10.0
        assert result["actively_exploited"] is True

    @pytest.mark.anyio
    async def test_handles_no_matching_cve(self, monkeypatch):
        enrichment._NVD_CACHE._store.clear()

        async def fake_get(url, *, params, headers):
            return _fake_response({"vulnerabilities": []})

        monkeypatch.setattr(enrichment, "_http_get", fake_get)

        result = await enrichment.nvd_lookup("CVE-9999-00000", "")

        assert result["cvss_score"] is None
        assert result["actively_exploited"] is None
