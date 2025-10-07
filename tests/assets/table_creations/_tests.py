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
    from models import A, B, C, G, H

    b = await B.create(name="b")
    c = await C.create(name="c")
    g = await G.create(name="g")
    h = await H.create(name="h")
    a = await A.create(name="a", b=b, c=c)
    f = await Foo.create(name="f", g=g)
    fh = await Foo.create(name="fh", h=h)

    assert a in (await A.filter(b=b))
    assert a in (await A.filter(c=c))
    assert f in (await Foo.filter(g=g))
    assert fh in (await Foo.filter(h=h))
