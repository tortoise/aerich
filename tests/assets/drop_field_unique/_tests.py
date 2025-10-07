import pytest
from models import UserTicketPackage as Foo
from settings import TORTOISE_ORM
from tortoise import Tortoise
from tortoise.exceptions import OperationalError

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


async def assert_not_unique():
    await Foo.create(package_order_id="1", qr_code="c")
    with pytest.raises(OperationalError):
        await Foo.create(package_order_id="1", qr_code="c")
    with pytest.raises(OperationalError):
        await Foo.create(package_order_id="2", qr_code="c")
    with pytest.raises(OperationalError):
        await Foo.create(package_order_id="1", qr_code="xxx")


@pytest.mark.anyio
async def test_1():
    await assert_not_unique()


@pytest.mark.anyio
async def test_2():
    await Foo.create(package_order_id="id", qr_code="code")
    await Foo.create(package_order_id="id", qr_code="code")
    await Foo.all().delete()


@pytest.mark.anyio
async def test_3():
    await assert_not_unique()


@pytest.mark.anyio
async def test_4():
    await Foo.all().delete()
    await Foo.create(package_order_id="id", qr_code="code")
    with pytest.raises(OperationalError):
        await Foo.create(package_order_id="id2", qr_code="code2")
    await Foo.create(package_order_id="id2", qr_code="code2", name="2")


@pytest.mark.anyio
async def test_5():
    await Foo.create(package_order_id="id3", qr_code="code3", name="2")
    await Foo.create(package_order_id="id4", qr_code="code4", name="2")
    await Foo.create(package_order_id="id5", qr_code="code5")
    await Foo.create(package_order_id="id6", qr_code="code6")
