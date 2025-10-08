import pytest

from aerich import TortoiseContext

try:
    from settings import TORTOISE_ORM  # type:ignore[import-not-found]
except ImportError:
    TORTOISE_ORM = None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def init_connections():
    async with TortoiseContext(TORTOISE_ORM):
        yield
