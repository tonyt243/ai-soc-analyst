# AI SOC Analyst — backend

FastAPI backend with a hand-written Claude tool-use agent loop. See
[`../CLAUDE.md`](../CLAUDE.md) for the full project plan.

## Setup

Requires Python 3.11+ (uses `StrEnum` and PEP 604 union syntax).

```sh
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements-dev.txt   # includes requirements.txt + pytest/httpx
copy .env.example .env                # then fill in ANTHROPIC_API_KEY
```

(Just running the server, no tests? `pip install -r requirements.txt` is enough.)

## Run

```sh
uvicorn app.main:app --reload
```

- `GET /health` — liveness check
- `GET /alerts/types` — the 5 synthetic alert types
- `POST /alerts/generate` — generate a synthetic alert (body: `{"type": "ssh_brute_force"}`, or `{}` for random)
- `GET /alerts` — list generated alerts (in-memory, resets on restart)
- `GET /investigate/{alert_id}/stream` — SSE stream of the investigation (runs the agent loop against the real Claude API — requires `ANTHROPIC_API_KEY`)

## Test

```sh
pytest
```

Covers every endpoint, including the agent loop itself, against a fake
Anthropic client (`tests/fakes.py`) — no network calls or API key needed to
run the suite. `tests/conftest.py` resets the in-memory alert store before
each test — it's a module-level dict, so tests would otherwise leak alerts
into each other.

## Status

Backend is functionally complete for v1 — see `CLAUDE.md` § Agent loop
design for how `app/agent/loop.py` works.
