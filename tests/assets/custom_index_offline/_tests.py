import pytest
from models import Foo
from settings import TORTOISE_ORM
from tortoise import Tortoise

from aerich import Command


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def init_connections():
    await Tortoise.init(TORTOISE_ORM)
    try:
        yield
    finally:
        await Command.aclose()


@pytest.mark.anyio
async def test_1():
    obj1 = await Foo.create(name="foo")
    assert obj1 in (await Foo.all())


@pytest.mark.anyio
async def test_2():
    obj2 = await Foo.create(name="foo2")
    assert obj2 in (await Foo.all())


@pytest.mark.anyio
async def test_3():
    obj3 = await Foo.create(name="foo3")
    assert obj3 in (await Foo.all())
