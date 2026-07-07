# AI SOC Analyst — Project Plan

An autonomous agent that triages security alerts like a Tier-1 SOC analyst: it
investigates using tools, reasons over evidence, and submits a structured
verdict. The whole investigation streams to a "glass-box" UI — every thought,
every tool call, every token, live — so the point of the demo is *watching it
think*, not just reading a final answer.

This is a portfolio project. The priority order is: (1) the agent loop is
correct and easy to reason about, (2) the UI makes the reasoning legible,
(3) everything else.

## Why hand-written, no LangChain

The goal is to understand every line of the agentic loop — message history
management, tool-result round-trips, streaming event handling, stop-reason
branching. A framework would hide exactly the mechanics this project exists
to demonstrate (to the author, and to anyone reviewing the code in an
interview). `anthropic` is the only Claude-related dependency.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python) | async-native, plays well with SSE and the async Anthropic client |
| Agent loop | Hand-written, `anthropic` SDK | full control, see above |
| Streaming (backend → frontend) | SSE (Server-Sent Events) | simpler than WebSockets for one-directional server push; native browser `EventSource` support |
| Frontend | Next.js 15 + TypeScript + Tailwind | scaffolded in a later session |
| Deploy | Railway (backend) + Vercel (frontend) | deliberately last — see § v2 scope |

## Model

Default model is `claude-opus-4-8` with adaptive thinking
(`thinking: {type: "adaptive", display: "summarized"}`) so the reasoning
shown in the glass-box UI is real model output, not a paraphrase. This is
the correct default for demo quality, but it is not the cheapest option —
if the number of alerts run during demos/interviews gets large, consider
`claude-sonnet-5` for cost. Don't downgrade without deciding this
explicitly; it's a quality/cost tradeoff, not a default.

Streaming is mandatory — thinking + tool calls + text over multiple
tool-use rounds can comfortably exceed the ~16K non-streaming safety margin,
and streaming is also what makes the glass-box UI possible in the first
place.

## v1 scope

- [x] Hand-written agent loop (`app/agent/loop.py`): stream from Claude,
      execute tool calls, feed results back, repeat until `submit_verdict`
      is called or the model ends its turn.
- [x] 4 tools: `enrich_ip`, `lookup_cve`, `get_log_context` (investigation
      tools, stubbed with synthetic data), `submit_verdict` (terminal tool —
      calling it ends the investigation).
- [x] 5 synthetic alert generators: SSH brute force, Log4Shell exploitation,
      port scan, data exfiltration, suspicious PowerShell.
- [x] SSE endpoint that streams every agent-loop event (thinking deltas,
      tool-call start/input/result, text, final verdict, token usage) to
      the frontend as they happen.
- [x] Live token/cost meter — accumulate `usage` across every turn of the
      loop and compute running cost from the model's per-token pricing.
- [x] Glass-box UI (Next.js): a feed of every thought/tool call as it
      streams, plus the meter and the final verdict card.

## Explicitly not in v1

- **RAG** — no vector store, no retrieval over past incidents. Investigation
  context comes only from the tool calls in a single session.
- **Evals** — no automated grading of verdict quality, no eval harness.
- Real external integrations — `enrich_ip`/`lookup_cve`/`get_log_context`
  return synthetic/stubbed data, not live API calls to VirusTotal, NVD, etc.
- Auth, multi-tenancy, persistence beyond in-memory/session state.
- Deployment — Railway/Vercel config comes once v1 works locally.

These are v2/v3 candidates once the core loop and UI are solid.

## v2 scope

v1 is complete except deploy. Deploy is being held deliberately until after
the two items below — the reasoning is that a live demo link is worth more
once there's something more substantial behind it than reasoning over
synthetic tool data, and the stack is simple enough (no DB, two services)
that deploying late shouldn't surface any nasty surprises.

Priority order:

1. [x] **Real tool integrations** — `enrich_ip` (AbuseIPDB) and `lookup_cve`
       (NVD) in `app/agent/tool_handlers.py` now call live APIs via
       `app/agent/enrichment.py`, which adds a per-provider in-memory TTL
       cache and sliding-window rate limiter. Both fall back to the
       original synthetic data whenever the relevant key
       (`SOC_ABUSEIPDB_API_KEY` / `SOC_NVD_API_KEY`) is unset *or* the live
       call fails — so the app and test suite still need zero keys and
       zero network access by default. Add real keys to `.env` to switch
       either tool to live mode. `get_log_context` stays synthetic — there's
       no real log source to query.
2. [ ] **Eval harness** — run the 5 alert types repeatedly against the real
       agent loop and grade verdict consistency (right MITRE technique,
       stable severity, remediation actually actionable). No framework
       needed for v1 of this either — a small script is enough to start.
3. [ ] **Deploy** — Railway (backend) + Vercel (frontend), once the above
       make the demo worth deploying.

Alert generation (`app/alerts/generators.py`) stays synthetic regardless —
there's no real log/SIEM source in this project, by design (see the top of
this doc: it's a demo of the agentic loop and glass-box UI, not a
production detection product).

## Backend structure

```
backend/
  app/
    main.py              FastAPI app: CORS, router mounting, health check
    config.py             Settings (API key, model, effort, CORS origins)
    agent/
      loop.py              The hand-written tool-use loop (core of the project)
      prompts.py           System prompt — SOC analyst persona + MITRE guidance
      tools.py             Tool JSON schemas (enrich_ip, lookup_cve, get_log_context, submit_verdict)
      tool_handlers.py     Tool implementations: enrich_ip/lookup_cve call
                            enrichment.py (live, with synthetic fallback);
                            get_log_context/submit_verdict stay synthetic
      enrichment.py         Live AbuseIPDB/NVD clients + per-provider TTL
                            cache and rate limiter (v2)
    alerts/
      models.py            Alert pydantic model
      generators.py        The 5 synthetic alert generators
    schemas/
      verdict.py           Verdict model: severity, MITRE technique, remediation, confidence
      events.py            SSE event models (one type per glass-box event)
    streaming/
      sse.py                Formats agent-loop events as SSE wire format
    routers/
      alerts.py             GET/POST endpoints for listing & generating alerts
      investigate.py         GET SSE endpoint — runs the agent loop, streams events
  tests/
  requirements.txt
  .env.example
  README.md
```

`agent/loop.py` is intentionally scaffolded but not implemented yet — that's
the next work session. Everything else in this list is either fully working
scaffolding or a clearly-marked stub returning synthetic data.

## Agent loop design

Implemented in `app/agent/loop.py`. Shape of `AgentLoop.run()`:

1. Build initial `messages` = `[{"role": "user", "content": alert_summary}]`.
2. Loop (capped at `MAX_TURNS = 15` — a safety net in case a confused model
   never calls `submit_verdict`):
   - Call `client.messages.stream(model=..., system=SYSTEM_PROMPT,
     tools=TOOLS, thinking={"type": "adaptive", "display": "summarized"},
     output_config={"effort": ...}, messages=messages)`.
   - As raw stream events arrive, translate `thinking_delta`/`text_delta`
     content-block deltas to glass-box SSE events and yield them upward.
     Tool-call inputs are *not* streamed incrementally — they're read off
     the accumulated final message instead (simpler, and the JSON input for
     these tools is small enough that the latency difference is invisible).
   - On `stream.get_final_message()`, accumulate `usage` into a running
     total and emit it as a `UsageUpdate` (cost computed via
     `app/agent/pricing.py`).
   - `stop_reason` of `refusal`, `max_tokens`, or anything other than
     `tool_use` ends the investigation with an `InvestigationError` — the
     model is expected to always reach a verdict via a tool call.
   - Execute each `tool_use` block via `tool_handlers`. `submit_verdict`'s
     input gets parsed into the `Verdict` pydantic model — if that raises
     (the model sent a malformed verdict), the tool_result comes back
     `is_error=True` and the loop continues instead of crashing, giving the
     model a chance to retry with valid fields.
   - If a valid verdict was captured this turn: emit `VerdictReady` and
     stop (no need to round-trip the trivial tool_result back to the API).
   - Otherwise: append the assistant turn (full `message.content`, which
     preserves thinking blocks for continued reasoning) and a user turn
     with all `tool_result` blocks, then continue the loop.

Router wiring: `get_agent_loop()` in `loop.py` is a FastAPI dependency
(`app/routers/investigate.py`) — this is what makes the router trivially
testable via `app.dependency_overrides` without hitting the real API (see
`tests/test_investigate.py`). `tests/test_agent_loop.py` tests the loop
itself against a fake Anthropic client (`tests/fakes.py`) that implements
just the `messages.stream()` async-context-manager surface the loop
actually touches — no network calls, no API key needed to run the suite.

## Glass-box UI requirements

- Every SSE event type from the backend gets its own visual treatment:
  thinking (italic/muted), tool call (name + input, then result once it
  arrives), text (normal), verdict (final card with severity color, MITRE
  technique, remediation).
- Token/cost meter updates live as usage events arrive — this is a
  deliberate "show the receipts" feature for a SOC-tooling portfolio piece.
- Nothing is buffered until the end — if the backend streamed it, the UI
  renders it as it arrives.
