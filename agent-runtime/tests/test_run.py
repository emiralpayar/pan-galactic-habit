"""ClaudeRuntime.run: the invariants agent-runtime/README.md says must be covered by tests.

These use a fake ClaudeSDKClient (monkeypatching `agent_runtime.claude._client`) so no
credential and no real CLI process is needed: the SDK session loop itself is trusted, only
this backend's checks around it are under test.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, SystemMessage, TextBlock, ToolUseBlock
from pydantic import BaseModel

import agent_runtime.claude as claude_module
from agent_runtime import (
    AssistantText,
    ClaudeConfig,
    ClaudeRuntime,
    SessionEnded,
    SessionRequest,
    Tool,
    ToolCalled,
    ToolSurface,
    ToolSurfaceError,
)


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


@pytest.fixture
def request_(surface: ToolSurface) -> SessionRequest:
    return SessionRequest(instructions="Be helpful.", tool_surface=surface, prompt="hi")


def _init(api_key_source: str = "none") -> SystemMessage:
    return SystemMessage(
        subtype="init",
        data={
            "tools": ["mcp__habit__get_item"],
            "mcp_servers": [{"name": "habit", "source": "sdk"}],
            "apiKeySource": api_key_source,
        },
    )


def _result(is_error: bool = False) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=is_error,
        num_turns=1,
        session_id="s",
    )


class _FakeClient:
    def __init__(self, messages: list[object]) -> None:
        self._messages = messages
        self.queried: list[str] = []

    async def query(self, prompt: str) -> None:
        self.queried.append(prompt)

    async def receive_response(self) -> AsyncIterator[object]:
        for message in self._messages:
            yield message


def _patch_client(
    monkeypatch: pytest.MonkeyPatch,
    messages: list[object],
    environment: dict[str, str] | None = None,
) -> None:
    @asynccontextmanager
    async def fake_client(
        request: SessionRequest, config: ClaudeConfig
    ) -> AsyncIterator[tuple[_FakeClient, dict[str, str]]]:
        yield _FakeClient(messages), environment or {}

    monkeypatch.setattr(claude_module, "_client", fake_client)


async def _run(request: SessionRequest) -> list[object]:
    runtime = ClaudeRuntime(ClaudeConfig(model="claude-sonnet-5"))
    return [event async for event in runtime.run(request)]


@pytest.mark.anyio
async def test_a_read_only_tool_call_is_reported(
    monkeypatch: pytest.MonkeyPatch, request_: SessionRequest
) -> None:
    _patch_client(
        monkeypatch,
        [
            _init(),
            AssistantMessage(
                content=[
                    TextBlock(text="Looking it up."),
                    ToolUseBlock(id="t1", name="mcp__habit__get_item", input={"id": 1}),
                ],
                model="claude-sonnet-5",
            ),
            _result(),
        ],
    )
    events = await _run(request_)
    assert events == [
        AssistantText("Looking it up."),
        ToolCalled("get_item", {"id": 1}),
        SessionEnded(is_error=False),
    ]


@pytest.mark.anyio
async def test_a_message_before_init_is_rejected(
    monkeypatch: pytest.MonkeyPatch, request_: SessionRequest
) -> None:
    _patch_client(
        monkeypatch,
        [AssistantMessage(content=[TextBlock(text="early")], model="claude-sonnet-5")],
    )
    with pytest.raises(ToolSurfaceError, match="did not report its tools first"):
        await _run(request_)


@pytest.mark.anyio
async def test_a_session_with_no_init_is_rejected(
    monkeypatch: pytest.MonkeyPatch, request_: SessionRequest
) -> None:
    _patch_client(monkeypatch, [])
    with pytest.raises(ToolSurfaceError, match="ended without reporting its tools"):
        await _run(request_)


@pytest.mark.anyio
async def test_a_tool_call_outside_the_surface_is_rejected(
    monkeypatch: pytest.MonkeyPatch, request_: SessionRequest
) -> None:
    _patch_client(
        monkeypatch,
        [
            _init(),
            AssistantMessage(
                content=[ToolUseBlock(id="t1", name="mcp__habit__delete_item", input={})],
                model="claude-sonnet-5",
            ),
        ],
    )
    with pytest.raises(ToolSurfaceError, match="delete_item"):
        await _run(request_)


@pytest.mark.anyio
async def test_a_tool_call_without_the_prefix_is_rejected(
    monkeypatch: pytest.MonkeyPatch, request_: SessionRequest
) -> None:
    _patch_client(
        monkeypatch,
        [
            _init(),
            AssistantMessage(
                content=[ToolUseBlock(id="t1", name="Bash", input={})], model="claude-sonnet-5"
            ),
        ],
    )
    with pytest.raises(ToolSurfaceError, match="Bash"):
        await _run(request_)


@pytest.mark.anyio
async def test_an_unexpected_credential_source_is_rejected(
    monkeypatch: pytest.MonkeyPatch, request_: SessionRequest
) -> None:
    _patch_client(monkeypatch, [_init(api_key_source="ANTHROPIC_API_KEY")])
    with pytest.raises(ToolSurfaceError, match="credential source"):
        await _run(request_)
