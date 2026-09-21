import pytest
from pydantic import BaseModel

from agent_runtime import Tool, ToolSurface, ToolSurfaceError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class ItemId(BaseModel):
    id: int


async def _get_item(arguments: ItemId) -> str:
    return f"item {arguments.id}"


GET_ITEM = Tool("get_item", "Read one item by id.", ItemId, _get_item)


@pytest.fixture
def surface() -> ToolSurface:
    return ToolSurface(tools=(GET_ITEM,))


@pytest.mark.anyio
async def test_valid_arguments_run_the_handler() -> None:
    assert await GET_ITEM.call({"id": 7}) == ("item 7", False)


@pytest.mark.anyio
async def test_invalid_arguments_are_an_error_and_do_not_run_the_handler() -> None:
    text, is_error = await GET_ITEM.call({"id": "not a number"})
    assert is_error
    assert text.startswith("Invalid arguments for get_item")


@pytest.mark.parametrize("name", ["Get", "get-item", "1item", "", "a" * 65, "mcp__x__y"])
def test_tool_names_are_restricted(name: str) -> None:
    with pytest.raises(ToolSurfaceError):
        Tool(name, "d", GET_ITEM.input_model, GET_ITEM.handler)


def test_duplicate_names_are_rejected() -> None:
    with pytest.raises(ToolSurfaceError):
        ToolSurface(tools=(GET_ITEM, GET_ITEM))


def test_surface_names_and_lookup(surface: ToolSurface) -> None:
    assert surface.names == frozenset({"get_item"})
    assert surface.get("get_item") is GET_ITEM
    assert surface.get("bash") is None
