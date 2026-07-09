"""The hand-written tool-use agent loop — the core of this project.

Shape: call Claude with streaming + adaptive thinking, translate stream
events to glass-box `AgentEvent`s as they arrive, then use the accumulated
final message to execute any tool calls and continue the conversation.
Ends when the model calls `submit_verdict`, refuses, runs out of tokens, or
ends its turn without calling a tool (all three of the latter are treated
as failures — the model is expected to always reach a verdict).
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

import anthropic
from pydantic import ValidationError

from app.agent.pricing import estimate_cost_usd
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tool_handlers import TOOL_HANDLERS
from app.agent.tools import TOOLS
from app.alerts.models import Alert
from app.config import get_settings
from app.schemas.events import (
    AgentEvent,
    InvestigationError,
    TextDelta,
    ThinkingDelta,
    ToolCallResult,
    ToolCallStarted,
    UsageUpdate,
    VerdictReady,
)
from app.schemas.verdict import Verdict

MAX_TOKENS = 8192
# Safety cap: if a confused model never calls submit_verdict, don't loop forever.
MAX_TURNS = 15

_USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


async def _execute_tool(block: Any) -> tuple[dict[str, Any], ToolCallResult, Verdict | None]:
    """Run one `tool_use` block and package its result for both the API
    round-trip (`tool_result` dict) and the glass-box stream (`ToolCallResult`).

    Callers run these concurrently via `asyncio.gather` — Claude's parallel
    tool calls (e.g. `enrich_ip` on two different IPs) shouldn't be forced
    through the network sequentially just because the loop yields events
    one at a time.
    """
    try:
        verdict = Verdict(**block.input) if block.name == "submit_verdict" else None
        output = await TOOL_HANDLERS[block.name](block.input)
        tool_result = {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output)}
        return tool_result, ToolCallResult(tool_use_id=block.id, name=block.name, output=output), verdict
    except (ValidationError, KeyError) as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        tool_result = {"type": "tool_result", "tool_use_id": block.id, "content": error_text, "is_error": True}
        return tool_result, ToolCallResult(tool_use_id=block.id, name=block.name, output=error_text, is_error=True), None


def _alert_prompt(alert: Alert) -> str:
    return (
        "Investigate this alert:\n\n"
        f"Type: {alert.type.value}\n"
        f"Title: {alert.title}\n"
        f"Source IP: {alert.source_ip}\n"
        f"Metadata: {json.dumps(alert.metadata)}\n\n"
        f"Raw log:\n{alert.raw_log}"
    )


class AgentLoop:
    def __init__(self, client: anthropic.AsyncAnthropic, model: str, effort: str) -> None:
        self.client = client
        self.model = model
        self.effort = effort

    async def run(self, alert: Alert) -> AsyncGenerator[AgentEvent, None]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": _alert_prompt(alert)}]
        usage_totals = {field: 0 for field in _USAGE_FIELDS}

        for _turn in range(MAX_TURNS):
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                thinking={"type": "adaptive", "display": "summarized"},
                output_config={"effort": self.effort},
                messages=messages,
            ) as stream:
                async for event in stream:
                    if event.type != "content_block_delta":
                        continue
                    if event.delta.type == "thinking_delta":
                        yield ThinkingDelta(text=event.delta.thinking)
                    elif event.delta.type == "text_delta":
                        yield TextDelta(text=event.delta.text)

                message = await stream.get_final_message()

            for field in _USAGE_FIELDS:
                usage_totals[field] += getattr(message.usage, field, 0) or 0
            yield UsageUpdate(**usage_totals, running_cost_usd=estimate_cost_usd(self.model, usage_totals))

            if message.stop_reason == "refusal":
                yield InvestigationError(message="Claude declined to investigate this alert.")
                return
            if message.stop_reason == "max_tokens":
                yield InvestigationError(message="Hit the token limit before reaching a verdict.")
                return
            if message.stop_reason != "tool_use":
                yield InvestigationError(
                    message=f"Investigation ended without a verdict (stop_reason={message.stop_reason})."
                )
                return

            tool_use_blocks = [block for block in message.content if block.type == "tool_use"]
            for block in tool_use_blocks:
                yield ToolCallStarted(tool_use_id=block.id, name=block.name, input=block.input)

            tool_results: list[dict[str, Any]] = []
            verdict: Verdict | None = None
            any_error = False

            for tool_result, tool_event, block_verdict in await asyncio.gather(
                *(_execute_tool(block) for block in tool_use_blocks)
            ):
                tool_results.append(tool_result)
                yield tool_event
                if block_verdict is not None:
                    verdict = block_verdict
                if tool_event.is_error:
                    any_error = True

            if any_error:
                verdict = None

            if verdict is not None:
                yield VerdictReady(verdict=verdict.model_dump())
                return

            messages.append({"role": "assistant", "content": message.content})
            messages.append({"role": "user", "content": tool_results})

        yield InvestigationError(message=f"Investigation did not reach a verdict within {MAX_TURNS} turns.")


@lru_cache
def _shared_client() -> anthropic.AsyncAnthropic:
    settings = get_settings()
    # Only pass api_key when we actually have one — an empty string would
    # override the SDK's own credential auto-detection (env var / `ant auth
    # login` profile) with a guaranteed-invalid key.
    if settings.anthropic_api_key:
        return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return anthropic.AsyncAnthropic()


def get_agent_loop() -> AgentLoop:
    settings = get_settings()
    return AgentLoop(client=_shared_client(), model=settings.model, effort=settings.effort)
