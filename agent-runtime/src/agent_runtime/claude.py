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

# The two credentials this backend supports. Exactly one may be set (ADR 0009).
_CREDENTIALS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")
_BASE_URL = "ANTHROPIC_BASE_URL"
# Any other ANTHROPIC_* variable is refused: it can select another account or model, add
# headers, or redirect traffic. So are the exact names below, which change how the CLI
# authenticates, where its traffic goes, or what code it loads.
_REFUSED_PREFIX = "ANTHROPIC_"
_REFUSED = (
    "CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK",
    "CLAUDE_CODE_CLIENT_CERT",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_VERTEX",
    "DYLD_INSERT_LIBRARIES",
    "LD_PRELOAD",
    "NODE_EXTRA_CA_CERTS",
    "NODE_OPTIONS",
    "ALL_PROXY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "http_proxy",
    "https_proxy",
)
# Overridden with an empty value in the child, so an unlisted one cannot slip through.
_NEUTRALIZED = (*_CREDENTIALS, _BASE_URL, "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL")


class CredentialError(RuntimeError):
    """The environment does not identify exactly one supported credential and endpoint."""


@dataclass(frozen=True)
class ClaudeConfig:
    """Committed configuration of the backend: which model, and any non-default endpoint."""

    model: str
    base_url: str | None = None


def build_environment(
    parent: Mapping[str, str], config: ClaudeConfig, config_dir: Path
) -> dict[str, str]:
    """Return the variables to hand the CLI, or raise CredentialError.

    The SDK merges these on top of the parent's environment and cannot remove anything from
    it (ADR 0009). So every variable that could change which account, model, or endpoint
    the CLI uses is refused when the parent sets it, and the common ones are also
    overridden here. The CLI reads its settings from an empty directory, not the user's.
    """
    present = [name for name in _CREDENTIALS if parent.get(name)]
    if len(present) > 1:
        raise CredentialError(f"Set exactly one Claude credential; found {', '.join(present)}.")
    refused = sorted(
        name
        for name, value in parent.items()
        if value
        and name not in _CREDENTIALS
        and name != _BASE_URL
        and (name.startswith(_REFUSED_PREFIX) or name in _REFUSED)
    )
    if refused:
        raise CredentialError(f"Unsupported variables are set: {', '.join(refused)}.")
    inherited_url = parent.get(_BASE_URL)
    if inherited_url and inherited_url != config.base_url:
        raise CredentialError(
            f"{_BASE_URL} is set but the committed configuration does not name it."
        )

    environment = dict.fromkeys(_NEUTRALIZED, "")
    environment.update({name: parent[name] for name in present})
    if config.base_url:
        environment[_BASE_URL] = config.base_url
    environment["CLAUDE_CONFIG_DIR"] = str(config_dir)
    # The CLI must not replace itself: a session runs exactly what the SDK pin installed.
    environment["DISABLE_AUTOUPDATER"] = "1"
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
        cwd=work_dir,
        env=environment,
    )


def _offered(init: SystemMessage) -> frozenset[str]:
    """The tools the model is offered, by Tool Surface name.

    A name that does not carry this backend's prefix is returned marked as unmapped, so it
    can never compare equal to a Tool Surface name.
    """
    return frozenset(
        name.removeprefix(_PREFIX) if name.startswith(_PREFIX) else f"unmapped:{name}"
        for name in init.data.get("tools", [])
    )


def _check_init(init: SystemMessage, tool_surface: ToolSurface) -> frozenset[str]:
    """Return the offered tools; raise if they, or the MCP servers, differ from the surface."""
    offered = _offered(init)
    if offered != tool_surface.names:
        extra = ", ".join(sorted(offered - tool_surface.names)) or "none"
        missing = ", ".join(sorted(tool_surface.names - offered)) or "none"
        raise ToolSurfaceError(
            f"The model would be offered tools that differ from the Tool Surface "
            f"(extra: {extra}; missing: {missing})."
        )
    servers = [
        (server.get("name"), server.get("source")) for server in init.data.get("mcp_servers", [])
    ]
    if servers != [(SERVER_NAME, "sdk")]:
        raise ToolSurfaceError(f"Unexpected MCP servers in the session: {servers}.")
    return offered


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
        surface = request.tool_surface
        async with _client(request, self._config) as client:
            await client.query(request.prompt)
            verified = False
            async for message in client.receive_response():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    _check_init(message, surface)
                    verified = True
                elif not verified:
                    # Nothing may be used before the tool list has been checked.
                    raise ToolSurfaceError("The session did not report its tools first.")
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield AssistantText(block.text)
                        elif isinstance(block, ToolUseBlock):
                            name = block.name.removeprefix(_PREFIX)
                            if not block.name.startswith(_PREFIX) or surface.get(name) is None:
                                raise ToolSurfaceError(f"The model called {block.name!r}.")
                            yield ToolCalled(name, block.input)
                elif isinstance(message, ResultMessage):
                    yield SessionEnded(is_error=message.is_error)
            if not verified:
                raise ToolSurfaceError("The session ended without reporting its tools.")

    async def effective_tools(self, tool_surface: ToolSurface) -> frozenset[str]:
        """Report the tools the CLI offers the model, without calling the model.

        The CLI reports them in its init message, sent right after the first prompt is
        submitted and before the model turns it into a call. A credential would let that
        turn start for real before this interrupts, so this refuses to run with one set;
        callers that need a credential (a live session) use `run` instead.
        """
        if any(name in os.environ for name in _CREDENTIALS):
            raise CredentialError(
                "effective_tools must not be called with a Claude credential set; "
                "it never calls the model."
            )
        request = SessionRequest(
            instructions="Reply with one word.", tool_surface=tool_surface, prompt="ping"
        )
        async with _client(request, self._config) as client:
            await client.query(request.prompt)
            async for message in client.receive_messages():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    await client.interrupt()
                    return _offered(message)
        raise ToolSurfaceError("The session ended without reporting its tools.")
