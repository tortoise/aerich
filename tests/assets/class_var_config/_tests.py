import pytest

from app.models import Foo


@pytest.mark.anyio
async def test_init_db():
    await Foo.create(name="foo")
    obj = await Foo.create(name="foo", age=1)
    assert not hasattr(obj, "age")


@pytest.mark.anyio
async def test_migrate_upgrade():
    obj = await Foo.create(name="foo", age=1)
    assert obj.age == 1
