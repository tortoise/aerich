import pytest
from models import Foo, Sth
from tortoise.exceptions import OperationalError


@pytest.mark.anyio
async def test_init_db():
    await Foo.create(a=1, b=1, c=1)
    with pytest.raises(OperationalError):
        await Foo.create(a=1, b=1, c=2)
    with pytest.raises(OperationalError):
        await Foo.create(a=1, b=2, c=1)
    with pytest.raises(OperationalError):
        await Sth.create(a=1, b=1, c=1, d=1)
        await Sth.create(a=1, b=1, c=1, d=1)


@pytest.mark.anyio
async def test_models_2():
    await Foo.create(a=2, b=2, c=2)
    await Foo.create(a=2, b=2, c=3)
    with pytest.raises(OperationalError):
        await Foo.create(a=2, b=2, c=3)
    await Sth.create(a=2, b=2, c=2, d=2)
    await Sth.create(a=3, b=2, c=2, d=2)
    with pytest.raises(OperationalError):
        await Sth.create(a=3, b=2, c=2, d=2)


@pytest.mark.anyio
async def test_models_3():
    await Sth.create(a=3, b=3, c=3, d=3, e=3, f=3)
    with pytest.raises(OperationalError):
        await Sth.create(a=3, b=3, c=3, d=3, e=3, f=4)
    with pytest.raises(OperationalError):
        await Sth.create(a=3, b=4, c=3, d=3, e=3, f=3)


@pytest.mark.anyio
async def test_models_4():
    from models import New

    await New.create(a=1, b=1)
    with pytest.raises(OperationalError):
        await New.create(a=1, b=1)


@pytest.mark.anyio
async def test_models_5():
    from models import New

    await New.create(a2=2, b2=2)
    with pytest.raises(OperationalError):
        await New.create(a2=2, b2=2)
