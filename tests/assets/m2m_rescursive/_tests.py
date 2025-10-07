import pytest
from models import Node
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
    obj1 = await Node.create(id=1)
    obj2 = await Node.create(id=2)
    await obj1.children.add(obj2)
    saved_obj = await Node.get(pk=obj1.pk)
    assert obj2 in (await saved_obj.children.all())


@pytest.mark.anyio
async def test_2():
    from models import Dummy

    await Dummy.create(name="foo")

    obj3 = await Node.create(id=3)
    obj4 = await Node.create(id=4)
    obj5 = await Node.create(id=5)
    await obj3.children.add(obj4, obj5)
    saved_obj = await Node.get(pk=obj3.pk)
    assert (await saved_obj.children.all()) == [obj4, obj5]
