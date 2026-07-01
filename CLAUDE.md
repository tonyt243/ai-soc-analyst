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
| Deploy | Railway (backend) + Vercel (frontend) | later phase, not v1 |

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

- [ ] Hand-written agent loop (`app/agent/loop.py`): stream from Claude,
      execute tool calls, feed results back, repeat until `submit_verdict`
      is called or the model ends its turn.
- [ ] 4 tools: `enrich_ip`, `lookup_cve`, `get_log_context` (investigation
      tools, stubbed with synthetic data), `submit_verdict` (terminal tool —
      calling it ends the investigation).
- [ ] 5 synthetic alert generators: SSH brute force, Log4Shell exploitation,
      port scan, data exfiltration, suspicious PowerShell.
- [ ] SSE endpoint that streams every agent-loop event (thinking deltas,
      tool-call start/input/result, text, final verdict, token usage) to
      the frontend as they happen.
- [ ] Live token/cost meter — accumulate `usage` across every turn of the
      loop and compute running cost from the model's per-token pricing.
- [ ] Glass-box UI (Next.js): a feed of every thought/tool call as it
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
      tool_handlers.py     Stub implementations of each tool
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

## Agent loop design (for the next session)

Rough shape of `AgentLoop.run()`:

1. Build initial `messages` = `[{"role": "user", "content": alert_summary}]`.
2. Loop:
   - Call `client.messages.stream(model=..., system=SYSTEM_PROMPT,
     tools=TOOLS, thinking={"type": "adaptive", "display": "summarized"},
     messages=messages)`.
   - As stream events arrive, translate each to a glass-box SSE event
     (thinking delta, text delta, tool-call started) and yield it upward.
   - On `stream.get_final_message()`, append the assistant turn to
     `messages`.
   - If `stop_reason != "tool_use"`: the model ended its turn without
     calling `submit_verdict` — this is a bug in the prompt/loop, not a
     normal exit; log and surface it.
   - Execute each `tool_use` block via `tool_handlers`. If one of them is
     `submit_verdict`, capture its input as the final verdict and stop
     the loop after sending the (trivial) tool_result back.
   - Append a `user` turn with all `tool_result` blocks, continue the loop.
3. Track `usage` (input/output/cache tokens) from every turn for the cost
   meter; emit a running total as its own SSE event type.

## Glass-box UI requirements

- Every SSE event type from the backend gets its own visual treatment:
  thinking (italic/muted), tool call (name + input, then result once it
  arrives), text (normal), verdict (final card with severity color, MITRE
  technique, remediation).
- Token/cost meter updates live as usage events arrive — this is a
  deliberate "show the receipts" feature for a SOC-tooling portfolio piece.
- Nothing is buffered until the end — if the backend streamed it, the UI
  renders it as it arrives.
