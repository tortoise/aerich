import re
from pathlib import Path

import pytest
from models import Foo
from settings import TORTOISE_ORM
from tortoise import Tortoise, connections

from aerich import Command
from aerich.exceptions import NotInitedError


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def init_connections():
    await Tortoise.init(TORTOISE_ORM)
    try:
        yield
    finally:
        await connections.close_all()


@pytest.mark.anyio
async def test_command_not_inited():
    command = Command(TORTOISE_ORM)
    message = "You have to call .init() first before migrate"
    with pytest.raises(NotInitedError, match=re.escape(message)):
        await command.migrate()


@pytest.mark.anyio
async def test_init_command_by_await():
    command = await Command(TORTOISE_ORM)
    if not list(Path("migrations/models").glob("*.py")):
        await command.init_db(safe=True)
    await command.migrate()
    await command.upgrade()
    await command.close()


@pytest.mark.anyio
async def test_init_command_by_async_with():
    async with Command(TORTOISE_ORM) as command:
        if not list(Path("migrations/models").glob("*.py")):
            await command.init_db(safe=True)
        await command.migrate()
        await command.upgrade()


@pytest.mark.anyio
async def test_init_command_by_init_func():
    command = Command(TORTOISE_ORM)
    await command.init()
    if not list(Path("migrations/models").glob("*.py")):
        await command.init_db(safe=True)
    await command.migrate()
    await command.upgrade()
    await command.close()


@pytest.mark.anyio
async def test_migrate_upgrade(init_connections):
    async with Command(TORTOISE_ORM) as command:
        await command.migrate()
        await command.upgrade()
    assert list(Path("migrations/models").glob("1_*.py"))
    await Foo.create(a=1, b=2)
