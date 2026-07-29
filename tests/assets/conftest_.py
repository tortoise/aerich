import contextlib
import importlib
from typing import Any

import pytest

with contextlib.suppress(KeyError):  # Use suppress to fix ruff check issue I001
    from aerich import TortoiseContext

_TORTOISE_ORM: dict[str, Any] | None = None
with contextlib.suppress(ImportError):
    settings = importlib.import_module("settings")

    _TORTOISE_ORM = settings.TORTOISE_ORM


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def init_connections():
    async with TortoiseContext(_TORTOISE_ORM):
        yield
