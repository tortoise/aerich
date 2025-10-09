import pytest
from models import User
from tortoise import connections
from tortoise.exceptions import OperationalError


async def _run_sql(statement: str) -> list[dict]:
    conn = connections.get("default")
    return await conn.execute_query_dict(statement)


async def select_even_team_m2m() -> list[dict]:
    return await _run_sql("SELECT * FROM event_team")


async def select_user_group_m2m() -> list[dict]:
    return await _run_sql("SELECT * FROM group_user")


@pytest.mark.anyio
async def test_1():
    from models import Event, Group, Team

    e1 = await Event.create(name="e1")
    t1 = await Team.create(name="t1")
    await e1.participants.add(t1)
    u1 = await User.create(name="u1")
    g1 = await Group.create(name="g1")
    await g1.users.add(u1)
    assert (await t1.events.all().count()) == 1
    assert (await u1.groups.all().count()) == 1
    val = await select_even_team_m2m()
    assert val == [{"event_id": e1.id, "team_id": t1.id}]


@pytest.mark.anyio
async def test_2():
    from models import Group

    u2 = await User.create(name="u2")
    g2 = await Group.create(name="g2")
    await g2.users.add(u2)
    assert (await u2.groups.all().count()) == 1
    val = await select_user_group_m2m()
    assert {"group_id": g2.id, "user_id": u2.id} in val

    with pytest.raises(OperationalError, match="no such table"):
        await select_even_team_m2m()


@pytest.mark.anyio
async def test_3():
    await User.create(name="u3")
    assert (await User.all().count()) >= 1
    with pytest.raises(OperationalError, match="no such table"):
        await select_user_group_m2m()
