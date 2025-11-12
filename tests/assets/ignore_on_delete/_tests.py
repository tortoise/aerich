import pytest
from models import Group, Profile, User


async def _test_cascade() -> None:
    group = await Group.create(name="g")
    user1 = await User.create(name="u1", group=group)
    user2 = await User.create(name="u2", group=group)
    profile1 = await Profile.create(age=1, user=user1)
    profile2 = await Profile.create(age=2, user=user2)
    await group.delete()
    assert not await User.filter(id__in=[user1.id, user2.id]).exists()
    assert not await Profile.filter(id__in=[profile1.id, profile2.id]).exists()


@pytest.mark.anyio
async def test_1():
    await _test_cascade()


@pytest.mark.anyio
async def test_2():
    await _test_cascade()
