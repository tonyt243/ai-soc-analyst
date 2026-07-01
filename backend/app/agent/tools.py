"""Tool JSON schemas passed as `tools=` to the Messages API.

Plain dicts, not the SDK's beta tool-runner decorators — the agent loop in
`loop.py` drives the call/execute/feed-back cycle by hand (see CLAUDE.md
for why), so these just need to be valid `input_schema` definitions.
"""

ENRICH_IP = {
    "name": "enrich_ip",
    "description": (
        "Look up threat-intelligence enrichment for an IP address: geolocation, "
        "ASN/organization, and a reputation score. Call this on any external IP "
        "involved in the alert before deciding how suspicious it is."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ip": {"type": "string", "description": "The IP address to look up"},
        },
        "required": ["ip"],
    },
}

LOOKUP_CVE = {
    "name": "lookup_cve",
    "description": (
        "Look up details for a CVE identifier: description, CVSS severity, and "
        "whether it's known to be actively exploited. Call this when the alert "
        "references or implies a specific vulnerability."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cve_id": {"type": "string", "description": "CVE identifier, e.g. 'CVE-2021-44228'"},
        },
        "required": ["cve_id"],
    },
}

GET_LOG_CONTEXT = {
    "name": "get_log_context",
    "description": (
        "Pull additional log entries for a host around the time of the alert, "
        "to see what happened immediately before and after. Use this to confirm "
        "or rule out a hypothesis about what the attacker did next."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Hostname to pull context for"},
            "minutes_before": {"type": "integer", "description": "How many minutes before the alert to include", "default": 5},
            "minutes_after": {"type": "integer", "description": "How many minutes after the alert to include", "default": 5},
        },
        "required": ["host"],
    },
}

SUBMIT_VERDICT = {
    "name": "submit_verdict",
    "description": (
        "Submit your final, structured verdict for this investigation. This ends "
        "the investigation — call it exactly once, after you've gathered enough "
        "evidence to support it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["informational", "low", "medium", "high", "critical"],
            },
            "mitre_technique": {
                "type": "string",
                "description": "MITRE ATT&CK technique ID and name, e.g. 'T1110 - Brute Force'",
            },
            "summary": {"type": "string", "description": "One or two sentence summary of what happened"},
            "remediation": {"type": "string", "description": "Concrete next step(s) for the on-call responder"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["severity", "mitre_technique", "summary", "remediation", "confidence"],
    },
}

TOOLS = [ENRICH_IP, LOOKUP_CVE, GET_LOG_CONTEXT, SUBMIT_VERDICT]
