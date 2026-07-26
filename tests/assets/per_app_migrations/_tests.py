import pytest
from auth.models import Users
from polls.models import Question
from tortoise import timezone


@pytest.mark.anyio
async def test_1():
    user = await Users.create(name="iron")
    assert user in (await Users.all())
    question = await Question.create(question_text="How are you?", pub_date=timezone.now())
    assert question in (await Question.all())


@pytest.mark.anyio
async def test_2():
    from auth.models import Role

    user = await Users.create(name="been")
    role = await Role.create(name="Member", user=user)
    assert role in (await user.roles.all())


@pytest.mark.anyio
async def test_3():
    from polls.models import Choice

    question = await Question.create(question_text="Where are you?", pub_date=timezone.now())
    choice = await Choice.create(choice_text="here", question=question)
    assert choice in (await question.choice_set.all())
