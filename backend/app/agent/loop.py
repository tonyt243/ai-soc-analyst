"""The hand-written tool-use agent loop — the core of this project.

Not implemented yet; this is next session's work. See CLAUDE.md
§ "Agent loop design" for the intended shape: stream from Claude, translate
stream events to `AgentEvent`s as they arrive, execute tool calls between
turns, and stop when `submit_verdict` is called.
"""

from collections.abc import AsyncGenerator

import anthropic

from app.alerts.models import Alert
from app.schemas.events import AgentEvent

# Implementation will need: app.agent.prompts.SYSTEM_PROMPT, app.agent.tools.TOOLS,
# app.agent.tool_handlers.TOOL_HANDLERS — see CLAUDE.md § Agent loop design.


class AgentLoop:
    def __init__(self, client: anthropic.AsyncAnthropic, model: str, effort: str) -> None:
        self.client = client
        self.model = model
        self.effort = effort

    async def run(self, alert: Alert) -> AsyncGenerator[AgentEvent, None]:
        """Investigate `alert`, yielding `AgentEvent`s as the investigation proceeds.

        The last event before the generator ends should be a `VerdictReady`
        (or an `InvestigationError` if the loop terminates without one).
        """
        raise NotImplementedError(
            "AgentLoop.run is scaffolded but not implemented — see CLAUDE.md "
            "§ Agent loop design for the intended shape."
        )
        yield  # pragma: no cover — makes this an async generator for type-checkers
