from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agent.loop import AgentLoop, get_agent_loop
from app.alerts import store
from app.alerts.models import Alert
from app.ratelimit import enforce_investigate_limit
from app.schemas.events import InvestigationError
from app.streaming.sse import to_sse

router = APIRouter(prefix="/investigate", tags=["investigate"])


@router.get("/{alert_id}/stream", dependencies=[Depends(enforce_investigate_limit)])
async def stream_investigation(
    alert_id: str, agent_loop: AgentLoop = Depends(get_agent_loop)
) -> EventSourceResponse:
    alert = store.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")

    return EventSourceResponse(_stream(agent_loop, alert))


async def _stream(agent_loop: AgentLoop, alert: Alert) -> AsyncGenerator[dict[str, str], None]:
    try:
        async for event in agent_loop.run(alert):
            yield to_sse(event)
    except Exception as exc:
        # Last-resort guard: an unhandled exception here (network failure,
        # API error) should end the SSE stream with a visible error event,
        # not hang the connection or 500 mid-stream.
        yield to_sse(InvestigationError(message=f"Unexpected error: {exc}"))
