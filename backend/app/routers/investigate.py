from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.alerts import store
from app.schemas.events import InvestigationError
from app.streaming.sse import to_sse

router = APIRouter(prefix="/investigate", tags=["investigate"])


@router.get("/{alert_id}/stream")
async def stream_investigation(alert_id: str) -> EventSourceResponse:
    alert = store.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")

    return EventSourceResponse(_not_implemented_stream())


async def _not_implemented_stream() -> AsyncGenerator[dict[str, str], None]:
    # AgentLoop.run() (app/agent/loop.py) isn't implemented yet — this keeps
    # the endpoint shape real so the frontend can be built against it now.
    yield to_sse(
        InvestigationError(
            message="Agent loop not implemented yet — see app/agent/loop.py"
        )
    )
