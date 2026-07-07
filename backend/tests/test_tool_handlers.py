"""Tests for the enrich_ip/lookup_cve dispatch logic in tool_handlers.py:
synthetic fallback when no API key is configured, live call when one is,
and graceful degradation back to synthetic data if the live call fails."""

import httpx
import pytest

from app.agent import tool_handlers
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestEnrichIp:
    @pytest.mark.anyio
    async def test_internal_ip_never_calls_out(self, monkeypatch):
        async def fail(*args, **kwargs):
            raise AssertionError("should not call AbuseIPDB for an internal IP")

        monkeypatch.setattr(tool_handlers, "abuseipdb_check", fail)

        result = await tool_handlers.enrich_ip({"ip": "10.0.0.5"})

        assert result["classification"] == "internal"

    @pytest.mark.anyio
    async def test_falls_back_to_synthetic_without_a_key(self, monkeypatch):
        monkeypatch.setenv("SOC_ABUSEIPDB_API_KEY", "")

        async def fail(*args, **kwargs):
            raise AssertionError("should not call AbuseIPDB with no key configured")

        monkeypatch.setattr(tool_handlers, "abuseipdb_check", fail)

        result = await tool_handlers.enrich_ip({"ip": "185.220.101.47"})

        assert result["classification"] == "external"
        assert isinstance(result["reputation_score"], int)

    @pytest.mark.anyio
    async def test_uses_live_result_when_key_is_configured(self, monkeypatch):
        monkeypatch.setenv("SOC_ABUSEIPDB_API_KEY", "test-key")

        async def fake_check(ip, api_key):
            assert api_key == "test-key"
            return {"ip": ip, "classification": "external", "reputation_score": 99}

        monkeypatch.setattr(tool_handlers, "abuseipdb_check", fake_check)

        result = await tool_handlers.enrich_ip({"ip": "1.2.3.4"})

        assert result["reputation_score"] == 99

    @pytest.mark.anyio
    async def test_falls_back_to_synthetic_when_live_call_fails(self, monkeypatch):
        monkeypatch.setenv("SOC_ABUSEIPDB_API_KEY", "test-key")

        async def fake_check(ip, api_key):
            raise httpx.ConnectTimeout("timed out")

        monkeypatch.setattr(tool_handlers, "abuseipdb_check", fake_check)

        result = await tool_handlers.enrich_ip({"ip": "1.2.3.4"})

        assert result["classification"] == "external"
        assert "failed" in result["notes"]


class TestLookupCve:
    @pytest.mark.anyio
    async def test_falls_back_to_synthetic_without_a_key(self, monkeypatch):
        monkeypatch.setenv("SOC_NVD_API_KEY", "")

        async def fail(*args, **kwargs):
            raise AssertionError("should not call NVD with no key configured")

        monkeypatch.setattr(tool_handlers, "nvd_lookup", fail)

        result = await tool_handlers.lookup_cve({"cve_id": "cve-2021-44228"})

        assert result["cve_id"] == "CVE-2021-44228"
        assert result["actively_exploited"] is True

    @pytest.mark.anyio
    async def test_uses_live_result_when_key_is_configured(self, monkeypatch):
        monkeypatch.setenv("SOC_NVD_API_KEY", "test-key")

        async def fake_lookup(cve_id, api_key):
            assert api_key == "test-key"
            return {"cve_id": cve_id, "description": "live", "cvss_score": 7.5, "actively_exploited": False}

        monkeypatch.setattr(tool_handlers, "nvd_lookup", fake_lookup)

        result = await tool_handlers.lookup_cve({"cve_id": "CVE-2024-00001"})

        assert result["description"] == "live"

    @pytest.mark.anyio
    async def test_falls_back_to_synthetic_when_live_call_fails(self, monkeypatch):
        monkeypatch.setenv("SOC_NVD_API_KEY", "test-key")

        async def fake_lookup(cve_id, api_key):
            raise httpx.HTTPStatusError("rate limited", request=None, response=None)

        monkeypatch.setattr(tool_handlers, "nvd_lookup", fake_lookup)

        result = await tool_handlers.lookup_cve({"cve_id": "CVE-2024-00001"})

        assert result["description"].startswith("No record found")
