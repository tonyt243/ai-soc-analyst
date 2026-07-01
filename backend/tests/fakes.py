"""Fakes standing in for the `anthropic.AsyncAnthropic` streaming interface.

`AgentLoop.run()` only ever touches `client.messages.stream(...)` as:

    async with client.messages.stream(...) as stream:
        async for event in stream:
            ...
        message = await stream.get_final_message()

These fakes implement exactly that surface with plain attribute-bag objects
(no real anthropic types involved) so agent-loop tests run with no network
calls and no API key.
"""

from typing import Any


class FakeDelta:
    def __init__(self, type: str, **kwargs: Any) -> None:
        self.type = type
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeStreamEvent:
    def __init__(self, type: str, delta: FakeDelta | None = None) -> None:
        self.type = type
        self.delta = delta


class FakeContentBlock:
    def __init__(self, type: str, **kwargs: Any) -> None:
        self.type = type
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeUsage:
    def __init__(
        self,
        input_tokens: int = 100,
        output_tokens: int = 50,
        cache_read_input_tokens: int = 0,
        cache_creation_input_tokens: int = 0,
    ) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = cache_read_input_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens


class FakeMessage:
    def __init__(self, content: list[FakeContentBlock], stop_reason: str, usage: FakeUsage | None = None) -> None:
        self.content = content
        self.stop_reason = stop_reason
        self.usage = usage or FakeUsage()


class FakeStream:
    """One turn's worth of raw stream events plus the final accumulated message."""

    def __init__(self, events: list[FakeStreamEvent], final_message: FakeMessage) -> None:
        self._events = events
        self._final_message = final_message

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for event in self._events:
            yield event

    async def get_final_message(self) -> FakeMessage:
        return self._final_message


class FakeStreamContextManager:
    def __init__(self, stream: FakeStream) -> None:
        self._stream = stream

    async def __aenter__(self) -> FakeStream:
        return self._stream

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


class FakeMessagesResource:
    """Pops one pre-scripted turn per `.stream()` call, in order."""

    def __init__(self, turns: list[tuple[list[FakeStreamEvent], FakeMessage]]) -> None:
        self._turns = list(turns)
        self.call_count = 0

    def stream(self, **kwargs: Any) -> FakeStreamContextManager:
        self.call_count += 1
        events, final_message = self._turns.pop(0)
        return FakeStreamContextManager(FakeStream(events, final_message))


class FakeAnthropicClient:
    def __init__(self, turns: list[tuple[list[FakeStreamEvent], FakeMessage]]) -> None:
        self.messages = FakeMessagesResource(turns)
