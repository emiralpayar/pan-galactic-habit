"""The AgentRuntime port (ADR 0004): what habit code depends on, and nothing else."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from agent_runtime.tools import ToolSurface


@dataclass(frozen=True)
class SessionRequest:
    """One agent session: the habit's memory, its Tool Surface, and the user's message."""

    instructions: str
    tool_surface: ToolSurface
    prompt: str


@dataclass(frozen=True)
class AssistantText:
    text: str


@dataclass(frozen=True)
class ToolCalled:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class SessionEnded:
    is_error: bool


type SessionEvent = AssistantText | ToolCalled | SessionEnded


class AgentRuntime(Protocol):
    """Runs sessions such that the model sees exactly the request's Tool Surface."""

    def run(self, request: SessionRequest) -> AsyncIterator[SessionEvent]:
        """Run a session. Raises ToolSurfaceError, before the model acts, on any mismatch."""
        ...

    async def effective_tools(self, tool_surface: ToolSurface) -> frozenset[str]:
        """Start a session with the production configuration and report the tools the model
        is offered, by Tool Surface name, without calling the model. The Tool Surface
        contract test compares this with the Tool Surface itself. A backend must refuse to
        run this with a credential set, since its only job is the credential-less check."""
        ...
