"""Stub tool implementations — synthetic data, no live external calls (v1 scope, see CLAUDE.md).

Each handler takes the parsed `tool_use.input` dict and returns whatever
should go back as the `tool_result` content. `submit_verdict` is handled
specially by the agent loop (it ends the investigation) but still has an
entry here so the dispatch table stays uniform.
"""

import hashlib
import random
from typing import Any, Callable

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


def enrich_ip(input: dict[str, Any]) -> dict[str, Any]:
    ip = input["ip"]
    # Deterministic per-IP pseudo-randomness so repeated lookups of the same
    # IP within one investigation return consistent enrichment data.
    seed = int(hashlib.sha256(ip.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    is_internal = ip.startswith("10.") or ip.startswith("192.168.")

    if is_internal:
        return {
            "ip": ip,
            "classification": "internal",
            "reputation_score": 0,
            "notes": "RFC1918 private address space — not externally routable.",
        }

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


def lookup_cve(input: dict[str, Any]) -> dict[str, Any]:
    cve_id = input["cve_id"].upper()
    if cve_id in _KNOWN_CVES:
        return {"cve_id": cve_id, **_KNOWN_CVES[cve_id]}
    return {
        "cve_id": cve_id,
        "description": "No record found for this CVE in the local database (synthetic tool — v1 has no live NVD lookup).",
        "cvss_score": None,
        "actively_exploited": None,
    }


def get_log_context(input: dict[str, Any]) -> dict[str, Any]:
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
        "notes": "Synthetic log context (v1 has no live log store) — extend this in a later session.",
    }


def submit_verdict(input: dict[str, Any]) -> dict[str, Any]:
    return {"status": "verdict_recorded"}


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "enrich_ip": enrich_ip,
    "lookup_cve": lookup_cve,
    "get_log_context": get_log_context,
    "submit_verdict": submit_verdict,
}
