"""The Tool Surface contract (ADR 0004): what the model is offered equals the Tool Surface.

Each backend starts with its production configuration and the installed CLI runtime; the
tools it reports are compared with the Tool Surface exactly. No model is called and no
credential is needed: the tool list is reported before the first model turn. A backend
whose effective tool list cannot be read is not enabled.
"""

import os
from collections.abc import Callable

import pytest
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    SystemMessage,
    create_sdk_mcp_server,
)
from pydantic import BaseModel

from agent_runtime import (
    AgentRuntime,
    ClaudeConfig,
    ClaudeRuntime,
    Tool,
    ToolSurface,
    ToolSurfaceError,
)
from agent_runtime.claude import _check_tools


class ItemId(BaseModel):
    id: int


async def _get_item(arguments: ItemId) -> str:
    return f"item {arguments.id}"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def surface() -> ToolSurface:
    return ToolSurface(tools=(Tool("get_item", "Read one item by id.", ItemId, _get_item),))


BACKENDS: dict[str, Callable[[], AgentRuntime]] = {
    "claude": lambda: ClaudeRuntime(ClaudeConfig(model="claude-sonnet-5")),
}


@pytest.fixture(autouse=True)
def _no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.anyio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_the_model_is_offered_exactly_the_tool_surface(
    backend: str, surface: ToolSurface
) -> None:
    assert await BACKENDS[backend]().effective_tools(surface) == surface.names


@pytest.mark.anyio
async def test_the_probe_can_see_built_in_tools_when_they_are_enabled() -> None:
    """Guards the guard: with built-ins enabled the report must contain them."""
    options = ClaudeAgentOptions(
        tools={"type": "preset", "preset": "claude_code"},
        mcp_servers={"habit": create_sdk_mcp_server("habit", tools=[])},
        setting_sources=[],
        env={"CLAUDE_CODE_OAUTH_TOKEN": "", "ANTHROPIC_API_KEY": "", "PATH": os.environ["PATH"]},
    )
    async with ClaudeSDKClient(options) as client:
        await client.query("ping")
        async for message in client.receive_messages():
            if isinstance(message, SystemMessage) and message.subtype == "init":
                await client.interrupt()
                assert "Bash" in message.data["tools"]
                return
    pytest.fail("No init message.")


def _init(tools: list[str]) -> SystemMessage:
    return SystemMessage(subtype="init", data={"tools": tools})


def test_an_extra_tool_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="extra: Bash"):
        _check_tools(_init(["mcp__habit__get_item", "Bash"]), surface)


def test_a_missing_tool_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="missing: mcp__habit__get_item"):
        _check_tools(_init([]), surface)


def test_a_server_the_surface_did_not_register_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError):
        _check_tools(_init(["mcp__habit__get_item", "mcp__other__write"]), surface)
