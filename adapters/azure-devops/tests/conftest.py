import pytest


@pytest.fixture
def anyio_backend() -> str:
    # The adapter is async; its tests run on asyncio only, which is what the app uses.
    return "asyncio"
