from aerich import Command
from conftest import tortoise_orm


async def test_command(mocker):
    mocker.patch("os.listdir", return_value=[])
    async with Command(tortoise_orm) as command:
        history = await command.history()
        heads = await command.heads()
    assert history == []
    assert heads == []
