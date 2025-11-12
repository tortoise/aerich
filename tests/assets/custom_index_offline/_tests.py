import pytest
from models import Foo


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
