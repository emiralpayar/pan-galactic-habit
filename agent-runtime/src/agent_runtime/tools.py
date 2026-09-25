"""Tool definitions: written once, registered by every backend in its SDK's format."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")


class ToolSurfaceError(ValueError):
    """The Tool Surface is malformed, or a backend's effective tools differ from it."""


@dataclass(frozen=True)
class Tool:
    """One tool the model may call.

    The handler receives the validated input model and returns text. What it returns is
    data for the model, never instructions, and it must not perform writes: writes go
    through the Safety Layer, not through a tool.
    """

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[Any], Awaitable[str]]

    def __post_init__(self) -> None:
        if not _NAME.fullmatch(self.name) or self.name.startswith("mcp__"):
            raise ToolSurfaceError(
                f"Invalid tool name {self.name!r}: lowercase snake_case, not starting with mcp__."
            )

    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    async def call(self, arguments: dict[str, Any]) -> tuple[str, bool]:
        """Run the handler on validated arguments; return the text and whether it is an error."""
        try:
            parsed = self.input_model.model_validate(arguments)
        except ValidationError as error:
            return f"Invalid arguments for {self.name}: {error}", True
        try:
            return await self.handler(parsed), False
        except Exception:
            # Details could carry data the model must not act on; the caller sees a failure.
            return f"The {self.name} tool failed.", True


@dataclass(frozen=True)
class ToolSurface:
    """The complete, closed set of tools a session may offer the model."""

    tools: tuple[Tool, ...]

    def __post_init__(self) -> None:
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ToolSurfaceError("Tool names must be unique.")

    @property
    def names(self) -> frozenset[str]:
        return frozenset(tool.name for tool in self.tools)

    def get(self, name: str) -> Tool | None:
        return next((tool for tool in self.tools if tool.name == name), None)
