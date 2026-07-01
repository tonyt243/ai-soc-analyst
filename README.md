# AI SOC Analyst

An autonomous agent that triages security alerts like a Tier-1 SOC analyst —
investigates using tools, reasons over the evidence, and submits a
structured verdict (severity, MITRE ATT&CK technique, remediation). The
entire investigation streams live to a "glass-box" UI: every thought,
every tool call, every token, as it happens — not just the final answer.

The agent loop is hand-written against the Claude API (no LangChain or
similar framework) — the point of this project is to show the mechanics of
an agentic loop clearly, not to hide them behind an abstraction.

## Status

Backend scaffold is up and tested; the agent loop itself is next.

| Piece | Status |
|---|---|
| 5 synthetic alert generators (SSH brute force, Log4Shell, port scan, data exfiltration, suspicious PowerShell) | ✅ done |
| Alert API (`generate` / `list` / `get`) | ✅ done |
| SSE event contract + streaming endpoint | ✅ scaffolded, tested |
| Tool schemas + stub handlers (`enrich_ip`, `lookup_cve`, `get_log_context`, `submit_verdict`) | ✅ done |
| Hand-written Claude tool-use agent loop | 🚧 next |
| Live token/cost meter | 🚧 depends on the loop |
| Glass-box frontend (Next.js) | ⏳ not started |
| Deploy (Railway + Vercel) | ⏳ not started |

## Stack

FastAPI (Python) backend, Claude API via a hand-written streaming tool-use
loop, Server-Sent Events for backend→frontend streaming, Next.js 15 +
TypeScript + Tailwind frontend (upcoming).

## Getting started

Backend setup, run, and test instructions: [`backend/README.md`](backend/README.md).

Full project plan, architecture rationale, and design notes: [`CLAUDE.md`](CLAUDE.md).
