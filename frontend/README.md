# AI SOC Analyst — frontend

Next.js glass-box UI: renders every event from the backend's SSE
investigation stream live (thinking, tool calls, text, token/cost meter,
final verdict). See [`../CLAUDE.md`](../CLAUDE.md) for the full project
plan.

## Setup

```sh
npm install
cp .env.local.example .env.local   # points at the backend, defaults to localhost:8000
```

## Run

```sh
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Requires the backend
running (see [`../backend/README.md`](../backend/README.md)) — generate an
alert from the sidebar, select it, and watch the investigation stream in.

## Structure

- `src/lib/types.ts` — mirrors the backend's `AgentEvent`/`Alert`/`Verdict` schemas
- `src/lib/feed.ts` — reduces the raw event stream into renderable feed blocks (merges consecutive thinking/text deltas)
- `src/hooks/useInvestigation.ts` — owns the `EventSource` connection and per-event state
- `src/components/` — one component per glass-box treatment (feed, usage meter, verdict card, alert picker)
