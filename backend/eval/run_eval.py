"""Eval harness (v2 scope, see CLAUDE.md): run each of the 5 synthetic alert
types once through the real agent loop — real Claude API calls, needs
ANTHROPIC_API_KEY — and grade the resulting verdicts.

Usage (from backend/):
    python -m eval.run_eval

This is a single-pass smoke check of verdict quality, not a statistical
sample — re-run by hand whenever you want to check again (after a prompt
tweak, a model change, etc.). Each alert type gets exactly one real
investigation; there's no built-in repeat loop.

Three checks per alert type:
  - MITRE technique matches the expected family for that alert type
  - Severity falls in the expected range for that alert type
  - Remediation is judged actionable by a second, cheap Claude call (LLM judge)

Ground truth (`_GROUND_TRUTH` below) is intentionally lenient — MITRE mapping
has real ambiguity, so each alert type accepts a small family of acceptable
techniques/severities rather than a single exact answer.
"""

import asyncio
import json

import anthropic

from app.agent.loop import get_agent_loop
from app.alerts.generators import generate_alert
from app.alerts.models import AlertType
from app.schemas.events import InvestigationError, UsageUpdate, VerdictReady

_GROUND_TRUTH = {
    AlertType.SSH_BRUTE_FORCE: {
        "technique_prefixes": ["T1110"],  # Brute Force
        "severities": {"high", "critical"},  # generator always ends in a successful login
    },
    AlertType.LOG4SHELL: {
        "technique_prefixes": ["T1190"],  # Exploit Public-Facing Application
        "severities": {"high", "critical"},  # generator always shows a confirmed JNDI callback
    },
    AlertType.PORT_SCAN: {
        "technique_prefixes": ["T1595"],  # Active Scanning
        "severities": {"informational", "low", "medium"},  # recon only, no compromise evidence
    },
    AlertType.DATA_EXFILTRATION: {
        "technique_prefixes": ["T1041", "T1048", "T1567"],  # Exfiltration family
        "severities": {"high", "critical"},  # large anomalous transfer + DLP hit
    },
    AlertType.SUSPICIOUS_POWERSHELL: {
        "technique_prefixes": ["T1059"],  # Command and Scripting Interpreter (incl. .001 PowerShell)
        "severities": {"medium", "high"},
    },
}

_JUDGE_MODEL = "claude-haiku-4-5"
_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "actionable": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": ["actionable", "reasoning"],
    "additionalProperties": False,
}


def _technique_ok(mitre_technique: str, prefixes: list[str]) -> bool:
    technique_id = mitre_technique.strip().split(" ")[0].upper()
    return any(technique_id.startswith(prefix) for prefix in prefixes)


async def _judge_remediation(client: anthropic.AsyncAnthropic, remediation: str) -> tuple[bool, str]:
    response = await client.messages.create(
        model=_JUDGE_MODEL,
        max_tokens=300,
        output_config={"format": {"type": "json_schema", "schema": _JUDGE_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    "You are grading SOC (Security Operations Center) remediation advice. "
                    "Actionable means a specific next step an on-call responder can execute "
                    "right now (e.g. block a named IP, disable a named account, isolate a named "
                    "host, patch a named component). Not actionable means vague security hygiene "
                    "('improve monitoring', 'review policies', 'follow best practices') with no "
                    "concrete action.\n\n"
                    f"Remediation to grade:\n{remediation}"
                ),
            }
        ],
    )
    text = next(block.text for block in response.content if block.type == "text")
    result = json.loads(text)
    return result["actionable"], result["reasoning"]


async def _run_one(alert_type: AlertType, client: anthropic.AsyncAnthropic) -> dict:
    alert = generate_alert(alert_type)

    verdict: dict | None = None
    error_message: str | None = None
    running_cost = 0.0

    async for event in get_agent_loop().run(alert):
        if isinstance(event, VerdictReady):
            verdict = event.verdict
        elif isinstance(event, InvestigationError):
            error_message = event.message
        elif isinstance(event, UsageUpdate):
            running_cost = event.running_cost_usd

    result = {
        "alert_type": alert_type.value,
        "alert_title": alert.title,
        "cost_usd": running_cost,
        "verdict": verdict,
    }

    if verdict is None:
        result["technique_ok"] = False
        result["severity_ok"] = False
        result["remediation_ok"] = False
        result["remediation_reasoning"] = f"no verdict reached ({error_message})"
        return result

    ground_truth = _GROUND_TRUTH[alert_type]
    result["technique_ok"] = _technique_ok(verdict["mitre_technique"], ground_truth["technique_prefixes"])
    result["severity_ok"] = verdict["severity"] in ground_truth["severities"]
    result["remediation_ok"], result["remediation_reasoning"] = await _judge_remediation(
        client, verdict["remediation"]
    )
    return result


async def main() -> None:
    client = get_agent_loop().client  # same client construction the real app uses

    results = []
    for alert_type in AlertType:
        print(f"Running {alert_type.value}...", flush=True)
        results.append(await _run_one(alert_type, client))

    print("\n" + "=" * 90)
    print(f"{'Alert type':<24}{'Technique':<12}{'Severity':<12}{'Remediation':<14}{'Cost':>8}")
    print("-" * 90)

    total_cost = 0.0
    passed = 0
    for r in results:
        total_cost += r["cost_usd"]
        all_ok = r["technique_ok"] and r["severity_ok"] and r["remediation_ok"]
        passed += int(all_ok)
        print(
            f"{r['alert_type']:<24}"
            f"{'PASS' if r['technique_ok'] else 'FAIL':<12}"
            f"{'PASS' if r['severity_ok'] else 'FAIL':<12}"
            f"{'PASS' if r['remediation_ok'] else 'FAIL':<14}"
            f"${r['cost_usd']:.4f}"
        )
        if r["verdict"]:
            print(f"    verdict: severity={r['verdict']['severity']}, technique={r['verdict']['mitre_technique']}")
        print(f"    remediation judge: {r['remediation_reasoning']}")

    print("-" * 90)
    print(f"{passed}/{len(results)} alert types fully passed all checks. Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
