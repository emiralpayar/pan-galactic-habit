"""The Tool Surface contract (ADR 0004): what the model is offered equals the Tool Surface.

Each backend starts with its production configuration and the installed CLI runtime; the
tools it reports are compared with the Tool Surface exactly. No model is called and no
credential is needed: the tool list is reported before the first model turn. A backend
whose effective tool list cannot be read is not enabled.
"""

import os
from collections.abc import Callable
from pathlib import Path

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
    CredentialError,
    Tool,
    ToolSurface,
    ToolSurfaceError,
)
from agent_runtime.claude import _check_init, build_environment


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
async def test_effective_tools_refuses_a_credential(
    surface: ToolSurface, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "tok")
    with pytest.raises(CredentialError, match="never calls the model"):
        await ClaudeRuntime(ClaudeConfig(model="claude-sonnet-5")).effective_tools(surface)


@pytest.mark.anyio
@pytest.mark.parametrize("backend", BACKENDS)
async def test_the_model_is_offered_exactly_the_tool_surface(
    backend: str, surface: ToolSurface
) -> None:
    assert await BACKENDS[backend]().effective_tools(surface) == surface.names


@pytest.mark.anyio
async def test_the_probe_can_see_built_in_tools_when_they_are_enabled(tmp_path: Path) -> None:
    """Guards the guard: with built-ins enabled the report must contain them."""
    options = ClaudeAgentOptions(
        tools={"type": "preset", "preset": "claude_code"},
        mcp_servers={"habit": create_sdk_mcp_server("habit", tools=[])},
        setting_sources=[],
        permission_mode="dontAsk",
        env=build_environment(os.environ, ClaudeConfig(model="claude-sonnet-5"), Path(tmp_path)),
    )
    async with ClaudeSDKClient(options) as client:
        await client.query("ping")
        async for message in client.receive_messages():
            if isinstance(message, SystemMessage) and message.subtype == "init":
                await client.interrupt()
                assert "Bash" in message.data["tools"]
                return
    pytest.fail("No init message.")


def _init(
    tools: list[str] | None,
    servers: list[str] | None = None,
    api_key_source: str = "none",
) -> SystemMessage:
    names = ["habit"] if servers is None else servers
    data: dict[str, object] = {"mcp_servers": [{"name": n, "source": "sdk"} for n in names]}
    if tools is not None:
        data["tools"] = tools
    data["apiKeySource"] = api_key_source
    return SystemMessage(subtype="init", data=data)


def test_an_extra_tool_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="extra: unmapped:Bash"):
        _check_init(_init(["mcp__habit__get_item", "Bash"]), surface, "none")


def test_a_missing_tool_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="missing: get_item"):
        _check_init(_init([]), surface, "none")


def test_a_server_the_surface_did_not_register_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError):
        _check_init(_init(["mcp__habit__get_item", "mcp__other__write"]), surface, "none")


def test_a_tool_without_the_prefix_never_matches_a_surface_name(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="unmapped:get_item"):
        _check_init(_init(["get_item"]), surface, "none")


def test_an_extra_mcp_server_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="MCP servers"):
        _check_init(
            _init(["mcp__habit__get_item"], servers=["habit", "connector"]), surface, "none"
        )


def test_an_exact_match_passes(surface: ToolSurface) -> None:
    assert _check_init(_init(["mcp__habit__get_item"]), surface, "none") == surface.names


def test_an_unexpected_credential_source_is_rejected(surface: ToolSurface) -> None:
    init = _init(["mcp__habit__get_item"], api_key_source="ANTHROPIC_API_KEY")
    with pytest.raises(ToolSurfaceError, match="credential source"):
        _check_init(init, surface, "none")


def test_a_missing_tools_list_is_rejected(surface: ToolSurface) -> None:
    with pytest.raises(ToolSurfaceError, match="tools list"):
        _check_init(_init(None), surface, "none")


def test_a_non_list_tools_value_is_rejected(surface: ToolSurface) -> None:
    init = SystemMessage(
        subtype="init",
        data={
            "tools": "mcp__habit__get_item",
            "mcp_servers": [{"name": "habit", "source": "sdk"}],
            "apiKeySource": "none",
        },
    )
    with pytest.raises(ToolSurfaceError, match="tools list"):
        _check_init(init, surface, "none")
