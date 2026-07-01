import pytest

from app.agent.loop import MAX_TURNS, AgentLoop
from app.alerts.generators import generate_ssh_brute_force
from app.schemas.events import (
    InvestigationError,
    TextDelta,
    ThinkingDelta,
    ToolCallResult,
    ToolCallStarted,
    UsageUpdate,
    VerdictReady,
)
from tests.fakes import FakeAnthropicClient, FakeContentBlock, FakeDelta, FakeMessage, FakeStreamEvent, FakeUsage

VALID_VERDICT_INPUT = {
    "severity": "high",
    "mitre_technique": "T1110 - Brute Force",
    "summary": "Successful SSH login after a burst of failed attempts from an external IP.",
    "remediation": "Disable the affected account and block the source IP at the perimeter firewall.",
    "confidence": 0.9,
}


async def _run(client, alert=None) -> list:
    loop = AgentLoop(client=client, model="claude-opus-4-8", effort="high")
    return [event async for event in loop.run(alert or generate_ssh_brute_force())]


def _deltas() -> list[FakeStreamEvent]:
    return [
        FakeStreamEvent("content_block_delta", FakeDelta("thinking_delta", thinking="Let me check this IP...")),
        FakeStreamEvent("content_block_delta", FakeDelta("text_delta", text="Investigating.")),
        # input_json_delta and other event types should be ignored, not crash the loop.
        FakeStreamEvent("content_block_delta", FakeDelta("input_json_delta", partial_json="{}")),
        FakeStreamEvent("content_block_stop"),
    ]


@pytest.mark.anyio
async def test_happy_path_tool_call_then_verdict():
    turn_1 = (
        _deltas(),
        FakeMessage(
            content=[FakeContentBlock("tool_use", id="tu_1", name="enrich_ip", input={"ip": "185.220.101.47"})],
            stop_reason="tool_use",
            usage=FakeUsage(input_tokens=100, output_tokens=50),
        ),
    )
    turn_2 = (
        _deltas(),
        FakeMessage(
            content=[FakeContentBlock("tool_use", id="tu_2", name="submit_verdict", input=VALID_VERDICT_INPUT)],
            stop_reason="tool_use",
            usage=FakeUsage(input_tokens=80, output_tokens=40),
        ),
    )
    client = FakeAnthropicClient([turn_1, turn_2])

    events = await _run(client)

    assert client.messages.call_count == 2
    assert any(isinstance(e, ThinkingDelta) for e in events)
    assert any(isinstance(e, TextDelta) for e in events)

    tool_starts = [e for e in events if isinstance(e, ToolCallStarted)]
    assert [e.name for e in tool_starts] == ["enrich_ip", "submit_verdict"]

    tool_results = [e for e in events if isinstance(e, ToolCallResult)]
    assert all(not e.is_error for e in tool_results)

    usage_events = [e for e in events if isinstance(e, UsageUpdate)]
    assert len(usage_events) == 2
    # Running totals accumulate across turns, not per-turn.
    assert usage_events[-1].input_tokens == 180
    assert usage_events[-1].output_tokens == 90
    assert usage_events[-1].running_cost_usd > usage_events[0].running_cost_usd

    assert isinstance(events[-1], VerdictReady)
    assert events[-1].verdict["severity"] == "high"
    assert events[-1].verdict["mitre_technique"] == "T1110 - Brute Force"


@pytest.mark.anyio
async def test_retries_after_invalid_verdict_input():
    invalid_verdict = {**VALID_VERDICT_INPUT, "confidence": 5.0}  # out of the [0, 1] range
    turn_1 = (
        [],
        FakeMessage(
            content=[FakeContentBlock("tool_use", id="tu_1", name="submit_verdict", input=invalid_verdict)],
            stop_reason="tool_use",
        ),
    )
    turn_2 = (
        [],
        FakeMessage(
            content=[FakeContentBlock("tool_use", id="tu_2", name="submit_verdict", input=VALID_VERDICT_INPUT)],
            stop_reason="tool_use",
        ),
    )
    client = FakeAnthropicClient([turn_1, turn_2])

    events = await _run(client)

    assert client.messages.call_count == 2  # the loop continued instead of stopping on the bad call

    tool_results = [e for e in events if isinstance(e, ToolCallResult)]
    assert tool_results[0].is_error is True
    assert tool_results[1].is_error is False

    assert isinstance(events[-1], VerdictReady)
    assert events[-1].verdict["confidence"] == 0.9


@pytest.mark.anyio
@pytest.mark.parametrize("stop_reason", ["end_turn", "max_tokens", "refusal"])
async def test_ends_with_error_when_no_verdict_is_reached(stop_reason):
    turn_1 = ([], FakeMessage(content=[], stop_reason=stop_reason))
    client = FakeAnthropicClient([turn_1])

    events = await _run(client)

    assert client.messages.call_count == 1
    assert isinstance(events[-1], InvestigationError)


@pytest.mark.anyio
async def test_stops_after_max_turns_without_a_verdict():
    # Every turn calls enrich_ip and never submit_verdict — the loop must
    # not spin forever waiting for a verdict that's never coming.
    non_terminal_turn = (
        [],
        FakeMessage(
            content=[FakeContentBlock("tool_use", id="tu", name="enrich_ip", input={"ip": "1.2.3.4"})],
            stop_reason="tool_use",
        ),
    )
    client = FakeAnthropicClient([non_terminal_turn] * MAX_TURNS)

    events = await _run(client)

    assert client.messages.call_count == MAX_TURNS
    assert isinstance(events[-1], InvestigationError)
    assert str(MAX_TURNS) in events[-1].message
