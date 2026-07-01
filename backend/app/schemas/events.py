"""The glass-box event contract.

Every one of these is a distinct SSE `event:` type the frontend renders
differently (see CLAUDE.md § Glass-box UI requirements). `agent/loop.py`
is the only thing that constructs these; `streaming/sse.py` is the only
thing that serializes them onto the wire.
"""

from typing import Any, Literal

from pydantic import BaseModel


class ThinkingDelta(BaseModel):
    type: Literal["thinking_delta"] = "thinking_delta"
    text: str


class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class ToolCallStarted(BaseModel):
    type: Literal["tool_call_started"] = "tool_call_started"
    tool_use_id: str
    name: str
    input: dict[str, Any]


class ToolCallResult(BaseModel):
    type: Literal["tool_call_result"] = "tool_call_result"
    tool_use_id: str
    name: str
    output: Any
    is_error: bool = False


class UsageUpdate(BaseModel):
    type: Literal["usage_update"] = "usage_update"
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    running_cost_usd: float


class VerdictReady(BaseModel):
    type: Literal["verdict_ready"] = "verdict_ready"
    verdict: dict[str, Any]


class InvestigationError(BaseModel):
    type: Literal["error"] = "error"
    message: str


AgentEvent = (
    ThinkingDelta
    | TextDelta
    | ToolCallStarted
    | ToolCallResult
    | UsageUpdate
    | VerdictReady
    | InvestigationError
)
