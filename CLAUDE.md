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
| Frontend animation | Framer Motion | feed items, verdict card, cost meter, alert controls — see § Glass-box UI requirements |
| Markdown rendering | `react-markdown` | Claude's thinking/text/verdict output frequently contains markdown (bold, lists) — rendered, not shown as raw asterisks |
| Deploy | Railway (backend) + Vercel (frontend) | deliberately last — see § v2 scope |

## Model

Default model is `claude-opus-4-8` with adaptive thinking
(`thinking: {type: "adaptive", display: "summarized"}`) so the reasoning
shown in the glass-box UI is real model output, not a paraphrase. This is
the correct default for demo quality, but it is not the cheapest option —
if the number of alerts run during demos/interviews gets large, consider
`claude-sonnet-5` for cost. Don't downgrade without deciding this
explicitly; it's a quality/cost tradeoff, not a default.

This was checked empirically, not just assumed: running `eval/run_eval.py`
against both models (one pass, all 5 alert types) had Opus 4.8 pass 4/5
checks at $0.33 total; Sonnet 5 passed 3/5 and got stuck in the tool-use
loop on the log4shell alert, burning all `MAX_TURNS` without ever calling
`submit_verdict` ($0.85 total, more expensive than Opus despite being the
"cheap" model, because of that one runaway investigation). One pass isn't
a statistical sample, so this isn't conclusive proof Sonnet can't do the
job — but it's a concrete reason to keep Opus as the default rather than
switching on the general "Sonnet 5 is near-Opus quality" reputation alone.
Re-run the eval on both models before revisiting this.

Prompt caching (`cache_control` on the system prompt / tools) was also
considered and deliberately **not** implemented: `count_tokens` showed the
static system+tools block is ~1,556 tokens and even a full turn-1 prompt
tops out around ~2,100 — both under Opus 4.8's 4,096-token minimum
cacheable prefix, so a cache breakpoint would silently do nothing for
typical 2-4-turn investigations on the default model. It would activate on
`claude-sonnet-5` (1,024-token minimum) or on unusually long
investigations — revisit if either changes.

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
2. [x] **Eval harness** — `backend/eval/run_eval.py` (`python -m eval.run_eval`
       from `backend/`) runs each of the 5 alert types once through the real
       agent loop (real Claude API) and grades each verdict: MITRE technique
       against a per-alert-type expected family, severity against a per-type
       expected range, and remediation actionability via a second, cheap
       LLM-judge call (`claude-haiku-4-5` + structured outputs). One pass,
       not a repeat loop — re-run by hand after prompt/model changes rather
       than looping N times per invocation. No framework, just a script.
3. [ ] **Deploy** — Railway (backend) + Vercel (frontend), once the above
       make the demo worth deploying. Rate limiting (`app/ratelimit.py`) is
       already in place ahead of this: per-IP + global in-memory limits on
       `POST /alerts/generate` and `GET /investigate/{id}/stream`, so a
       public demo link can't run up the Anthropic API bill — see the
       module docstring for the exact numbers and reasoning.

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
    ratelimit.py           Per-IP + global in-memory rate limits on the
                            costly public endpoints (v2 deploy prep)
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
  eval/
    run_eval.py            Eval harness (v2) — see § v2 scope item 2
  tests/
  requirements.txt
  .env.example
  README.md
```

Everything above is fully implemented (v1 + v2 items 1 and 2 are done — see
§ v2 scope). Only deploy config remains.

Tool calls within a single turn run concurrently (`asyncio.gather`) rather
than sequentially — see § Agent loop design below.

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
   - Execute all `tool_use` blocks from the turn concurrently via
     `asyncio.gather` (`_execute_tool` in `loop.py`) — Claude can request
     several tools in one turn (e.g. `enrich_ip` on two IPs) and there's no
     reason to serialize independent network calls. `ToolCallStarted` is
     emitted for every block up front, then `ToolCallResult`s stream once
     the gather resolves, in the same order as the blocks (not completion
     order). `submit_verdict`'s input gets parsed into the `Verdict`
     pydantic model — if that raises (the model sent a malformed verdict),
     the tool_result comes back `is_error=True` and the loop continues
     instead of crashing, giving the model a chance to retry with valid
     fields; an error on *any* block in the turn invalidates a verdict
     parsed elsewhere in that same turn.
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

## Frontend structure

```
frontend/
  src/
    app/
      page.tsx              Top-level layout: sidebar (alerts) + main panel
      layout.tsx             Root layout, forces dark theme
      globals.css            Dark "SOC console" design tokens (see below)
    components/
      AlertPanel.tsx         Generate-alert buttons + alert list (sidebar)
      RawLogPanel.tsx        Shows the selected alert's raw_log above the feed
      InvestigationFeed.tsx  Renders thinking/text/tool_call feed items
      UsageMeter.tsx         Live token/cost stat bar
      VerdictCard.tsx        Final verdict card
      Markdown.tsx           Shared react-markdown wrapper (theme-styled)
    hooks/
      useInvestigation.ts    Owns the SSE EventSource; exposes state + stop()
      useAlert.ts            Fetches full alert detail (incl. raw_log) by id
    lib/
      api.ts                 Backend fetch helpers
      feed.ts                Reduces AgentEvents into FeedItems (merges deltas)
      feed.test.ts            Unit tests for feed.ts (vitest — `npm test`)
      types.ts                Mirrors backend/app/schemas/events.py
      labels.ts               Alert-type labels + severity color/glow tokens
```

`feed.ts` is the only pure, easily-unit-tested piece of frontend logic
(everything else is components/hooks tied to SSE + the DOM), so it's the
one file with real test coverage — `npm test` runs vitest. Not a full
frontend test suite by design; this project's testing investment is
concentrated on the backend (see `backend/README.md` § Test).

## Glass-box UI requirements

- Every SSE event type from the backend gets its own visual treatment:
  thinking (italic/muted, left accent border), tool call (name + input,
  then result once it arrives), text (normal), verdict (final card with
  severity color/glow, MITRE technique, remediation).
- Token/cost meter updates live as usage events arrive — this is a
  deliberate "show the receipts" feature for a SOC-tooling portfolio piece.
- Nothing is buffered until the end — if the backend streamed it, the UI
  renders it as it arrives.
- Visual theme is a dark "SOC console" (forced dark, not OS-preference
  dependent — see `app/globals.css` design tokens: `void`/`surface`/
  `accent`/etc.), not the generic light/dark Tailwind default. Framer
  Motion animates every event as it streams in (fade/slide-in feed items,
  a blinking caret on the actively-streaming block, a spring-entrance
  verdict card with severity-colored glow, a "ticking" cost meter) so the
  live investigation reads as active, not static.
- Claude's thinking/text/verdict output is rendered through `react-markdown`
  (`components/Markdown.tsx`), not raw strings — the model frequently emits
  markdown (bold, lists) that would otherwise show up as literal asterisks.
- The raw alert log (`Alert.raw_log`) is shown in `RawLogPanel`, pinned
  above the feed for the whole investigation — without it there's no way
  for a viewer to see the evidence the agent's reasoning is grounded in.
- A **Stop** button (next to the live pulsing indicator, shown only while
  `status === "running"`) closes the SSE connection client-side, which also
  cancels the backend's streaming generator (`sse-starlette` detects the
  disconnect) — so it actually halts further agent-loop turns, not just the
  UI display. See `useInvestigation.ts`'s `stop()`.
