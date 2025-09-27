import pytest
from models import DataLibGroup
from settings import TORTOISE_ORM
from tortoise import Tortoise, connections


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def init_connections():
    await Tortoise.init(TORTOISE_ORM)
    try:
        yield
    finally:
        await connections.close_all()


@pytest.mark.anyio
async def test_1():
    obj1 = await DataLibGroup.create(name="parent")
    obj2 = await DataLibGroup.create(name="child", parent=obj1)
    assert obj2 in (await obj1.by_children_list.all())


@pytest.mark.anyio
async def test_2():
    from models import DataLibItem

    group = await DataLibGroup.create(name="group")
    item = await DataLibItem.create(id=1)
    await item.by_group_list.add(group)
    saved_item = await DataLibItem.get(pk=item.pk)
    assert group in (await saved_item.by_group_list.all())
