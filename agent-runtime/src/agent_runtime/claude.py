"""Claude backend: the Claude Agent SDK, locked to the request's Tool Surface (ADR 0004)."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)

from agent_runtime.port import (
    AssistantText,
    SessionEnded,
    SessionEvent,
    SessionRequest,
    ToolCalled,
)
from agent_runtime.tools import Tool, ToolSurface, ToolSurfaceError

SERVER_NAME = "habit"
_PREFIX = f"mcp__{SERVER_NAME}__"

# The two credentials this backend supports. Exactly one may be set (ADR 0004).
_CREDENTIALS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")
# Other ways of authenticating or of redirecting the CLI. This backend supports none of
# them: refuse to start if the parent has one set, and neutralize it in the child.
_UNSUPPORTED = (
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_FOUNDRY_API_KEY",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
)
_BASE_URL = "ANTHROPIC_BASE_URL"
# Never set this: it would let a session skip the SDK's CLI version check.
_FORBIDDEN = ("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK",)


class CredentialError(RuntimeError):
    """The environment does not identify exactly one supported credential and endpoint."""


@dataclass(frozen=True)
class ClaudeConfig:
    """Committed configuration of the backend: which model, and any non-default endpoint."""

    model: str
    base_url: str | None = None
    cli_path: Path | None = None


def build_environment(
    parent: Mapping[str, str], config: ClaudeConfig, config_dir: Path
) -> dict[str, str]:
    """Return the variables to hand the CLI, or raise CredentialError.

    The SDK merges these on top of the parent's environment and cannot remove anything from
    it. So every variable that could change which account or endpoint the CLI uses is
    either refused (when the parent sets it) or overridden here, and the CLI reads its
    settings from an empty directory instead of the user's own.
    """
    present = [name for name in _CREDENTIALS if parent.get(name)]
    if len(present) > 1:
        raise CredentialError(f"Set exactly one Claude credential; found {', '.join(present)}.")
    unsupported = [name for name in _UNSUPPORTED + _FORBIDDEN if parent.get(name)]
    if unsupported:
        raise CredentialError(f"Unsupported variables are set: {', '.join(unsupported)}.")
    inherited_url = parent.get(_BASE_URL)
    if inherited_url and inherited_url != config.base_url:
        raise CredentialError(
            f"{_BASE_URL} is set but the committed configuration does not name it."
        )

    environment = dict.fromkeys((*_CREDENTIALS, *_UNSUPPORTED, _BASE_URL), "")
    environment.update({name: parent[name] for name in present})
    if config.base_url:
        environment[_BASE_URL] = config.base_url
    environment["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return environment


def _build_server(tool_surface: ToolSurface) -> Any:
    sdk_tools = []
    for definition in tool_surface.tools:
        sdk_tools.append(_register(definition))
    return create_sdk_mcp_server(SERVER_NAME, tools=sdk_tools)


def _register(definition: Tool) -> Any:
    @tool(definition.name, definition.description, definition.input_schema())
    async def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        text, is_error = await definition.call(arguments)
        return {"content": [{"type": "text", "text": text}], "is_error": is_error}

    return handler


def _options(
    request: SessionRequest, config: ClaudeConfig, config_dir: Path, work_dir: Path
) -> ClaudeAgentOptions:
    environment = build_environment(os.environ, config, config_dir)
    return ClaudeAgentOptions(
        tools=[],
        allowed_tools=[_PREFIX + name for name in sorted(request.tool_surface.names)],
        setting_sources=[],
        strict_mcp_config=True,
        permission_mode="dontAsk",
        mcp_servers={SERVER_NAME: _build_server(request.tool_surface)},
        system_prompt=request.instructions,
        model=config.model,
        cli_path=config.cli_path,
        cwd=work_dir,
        env=environment,
    )


def _check_tools(init: SystemMessage, tool_surface: ToolSurface) -> frozenset[str]:
    """Return the offered tools by Tool Surface name; raise if they differ from the surface."""
    offered = frozenset(init.data.get("tools", []))
    expected = frozenset(_PREFIX + name for name in tool_surface.names)
    if offered != expected:
        extra = ", ".join(sorted(offered - expected)) or "none"
        missing = ", ".join(sorted(expected - offered)) or "none"
        raise ToolSurfaceError(
            f"The model would be offered tools that differ from the Tool Surface "
            f"(extra: {extra}; missing: {missing})."
        )
    return frozenset(name.removeprefix(_PREFIX) for name in offered)


@asynccontextmanager
async def _client(request: SessionRequest, config: ClaudeConfig) -> AsyncIterator[ClaudeSDKClient]:
    with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as work_dir:
        options = _options(request, config, Path(config_dir), Path(work_dir))
        async with ClaudeSDKClient(options) as client:
            yield client


class ClaudeRuntime:
    """AgentRuntime backed by the Claude Agent SDK."""

    def __init__(self, config: ClaudeConfig) -> None:
        self._config = config

    async def run(self, request: SessionRequest) -> AsyncIterator[SessionEvent]:
        async with _client(request, self._config) as client:
            await client.query(request.prompt)
            verified = False
            async for message in client.receive_response():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    _check_tools(message, request.tool_surface)
                    verified = True
                elif not verified:
                    # Nothing may happen before the tool list has been checked.
                    raise ToolSurfaceError("The session did not report its tools first.")
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield AssistantText(block.text)
                        elif isinstance(block, ToolUseBlock):
                            yield ToolCalled(block.name.removeprefix(_PREFIX), block.input)
                elif isinstance(message, ResultMessage):
                    yield SessionEnded(is_error=message.is_error)

    async def effective_tools(self, tool_surface: ToolSurface) -> frozenset[str]:
        request = SessionRequest(
            instructions="Reply with one word.", tool_surface=tool_surface, prompt="ping"
        )
        async with _client(request, self._config) as client:
            await client.query(request.prompt)
            async for message in client.receive_messages():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    offered = frozenset(message.data.get("tools", []))
                    await client.interrupt()
                    return frozenset(name.removeprefix(_PREFIX) for name in offered)
        raise ToolSurfaceError("The session ended without reporting its tools.")
