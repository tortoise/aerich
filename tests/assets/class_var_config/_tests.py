import pytest
from aerich import Command
from tortoise import Tortoise

from app.core.config import settings
from app.models import Foo


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def init_connections():
    await Tortoise.init(settings.TORTOISE_ORM)
    try:
        yield
    finally:
        await Command.aclose()


@pytest.mark.anyio
async def test_init_db():
    await Foo.create(name="foo")
    obj = await Foo.create(name="foo", age=1)
    assert not hasattr(obj, "age")


@pytest.mark.anyio
async def test_migrate_upgrade():
    obj = await Foo.create(name="foo", age=1)
    assert obj.age == 1
