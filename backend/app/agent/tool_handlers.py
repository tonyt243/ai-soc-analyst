"""Tool implementations invoked by the agent loop.

`enrich_ip` and `lookup_cve` call live providers (AbuseIPDB, NVD — see
app/agent/enrichment.py) when the corresponding API key is configured, and
fall back to synthetic data otherwise so the app and test suite still work
with zero keys set (see CLAUDE.md v1/v2 scope). A live call that fails
(network error, rate limit, bad key) also falls back rather than raising —
a degraded tool result the model can reason around beats crashing the whole
investigation over one flaky provider.

`get_log_context` stays synthetic — there's no real log source in this
project by design. Each handler takes the parsed `tool_use.input` dict and
returns whatever should go back as the `tool_result` content. `submit_verdict`
is handled specially by the agent loop (it ends the investigation) but still
has an entry here so the dispatch table stays uniform. All handlers are
async so the loop can await them uniformly regardless of whether a given
call hits the network.
"""

import hashlib
import random
from typing import Any, Awaitable, Callable

import httpx

from app.agent.enrichment import abuseipdb_check, nvd_lookup
from app.config import get_settings

_KNOWN_CVES = {
    "CVE-2021-44228": {
        "description": "Apache Log4j2 JNDI features do not protect against attacker-controlled "
        "LDAP and other JNDI related endpoints (Log4Shell). Allows remote code execution.",
        "cvss_score": 10.0,
        "actively_exploited": True,
    },
    "CVE-2023-23397": {
        "description": "Microsoft Outlook elevation of privilege vulnerability via NTLM hash leak.",
        "cvss_score": 9.8,
        "actively_exploited": True,
    },
}


def _synthetic_enrich_ip(ip: str) -> dict[str, Any]:
    # Deterministic per-IP pseudo-randomness so repeated lookups of the same
    # IP within one investigation return consistent enrichment data.
    seed = int(hashlib.sha256(ip.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    return {
        "ip": ip,
        "classification": "external",
        "country": rng.choice(["RU", "CN", "NL", "RO", "VN", "BR"]),
        "asn_org": rng.choice(["DigitalOcean LLC", "M247 Europe", "Chang Way Technologies", "OVH SAS"]),
        "reputation_score": rng.randint(60, 98),  # 0-100, higher = worse
        "known_malicious": rng.random() > 0.35,
        "notes": "Seen in threat-intel feeds associated with scanning/brute-force activity."
        if rng.random() > 0.4
        else "No strong prior signal beyond reputation score.",
    }


def _synthetic_lookup_cve(cve_id: str) -> dict[str, Any]:
    if cve_id in _KNOWN_CVES:
        return {"cve_id": cve_id, **_KNOWN_CVES[cve_id]}
    return {
        "cve_id": cve_id,
        "description": "No record found for this CVE in the local database (synthetic fallback — "
        "no SOC_NVD_API_KEY configured, or the live NVD lookup failed).",
        "cvss_score": None,
        "actively_exploited": None,
    }


async def enrich_ip(input: dict[str, Any]) -> dict[str, Any]:
    ip = input["ip"]
    if ip.startswith("10.") or ip.startswith("192.168."):
        return {
            "ip": ip,
            "classification": "internal",
            "reputation_score": 0,
            "notes": "RFC1918 private address space — not externally routable.",
        }

    api_key = get_settings().abuseipdb_api_key
    if not api_key:
        return _synthetic_enrich_ip(ip)
    try:
        return await abuseipdb_check(ip, api_key)
    except httpx.HTTPError as exc:
        result = _synthetic_enrich_ip(ip)
        result["notes"] = f"Live AbuseIPDB lookup failed ({exc}); falling back to synthetic data. {result['notes']}"
        return result


async def lookup_cve(input: dict[str, Any]) -> dict[str, Any]:
    cve_id = input["cve_id"].upper()

    api_key = get_settings().nvd_api_key
    if not api_key:
        return _synthetic_lookup_cve(cve_id)
    try:
        return await nvd_lookup(cve_id, api_key)
    except httpx.HTTPError:
        return _synthetic_lookup_cve(cve_id)


async def get_log_context(input: dict[str, Any]) -> dict[str, Any]:
    host = input["host"]
    before = input.get("minutes_before", 5)
    after = input.get("minutes_after", 5)
    return {
        "host": host,
        "window_minutes": {"before": before, "after": after},
        "entries": [
            f"{host}: no anomalous process activity in the {before} minutes preceding the alert",
            f"{host}: standard authentication and cron activity resumed {after} minutes after the alert",
        ],
        "notes": "Synthetic log context — no real log/SIEM source in this project (by design, see CLAUDE.md).",
    }


async def submit_verdict(input: dict[str, Any]) -> dict[str, Any]:
    return {"status": "verdict_recorded"}


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {
    "enrich_ip": enrich_ip,
    "lookup_cve": lookup_cve,
    "get_log_context": get_log_context,
    "submit_verdict": submit_verdict,
}
