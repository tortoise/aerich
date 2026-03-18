import pytest
from tortoise.exceptions import OperationalError


@pytest.mark.anyio
async def test_1():
    from models import User

    user = await User.create(age=1)
    assert user.pk >= 1


@pytest.mark.anyio
async def test_2():
    from models import Users

    user = await Users.create(age=1)
    assert user.pk >= 2
    assert (await Users.filter(age=1).count()) == 2


@pytest.mark.anyio
async def test_3():
    from models import Member, UserAge

    user = await UserAge.get(id=1)
    member = await Member.create(user=user, name="m1")
    assert member.pk >= 1
    assert (await Member.filter(user__age=1).count()) == 1


@pytest.mark.anyio
async def test_4():
    from models import Users

    with pytest.raises(OperationalError):
        await Users.first()
