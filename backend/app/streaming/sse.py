"""Turns an `AgentEvent` into the dict shape `sse_starlette.EventSourceResponse` expects."""

from app.schemas.events import AgentEvent


def to_sse(event: AgentEvent) -> dict[str, str]:
    return {"event": event.type, "data": event.model_dump_json()}
