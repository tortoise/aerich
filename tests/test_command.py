import shutil

from aerich import Command
from conftest import tortoise_orm
from tests._utils import prepare_py_files, requires_dialect, run_shell


async def test_command(mocker):
    mocker.patch("os.listdir", return_value=[])
    async with Command(tortoise_orm) as command:
        history = await command.history()
        heads = await command.heads()
    assert history == []
    assert heads == []


@requires_dialect("sqlite")
def test_await_command(tmp_work_dir):
    prepare_py_files("command_programmatically")
    run_shell("aerich init -t settings.TORTOISE_ORM", capture_output=False)
    output = run_shell("pytest -s _tests.py::test_command_not_inited")
    assert "error" not in output.lower()
    output = run_shell("pytest -s _tests.py::test_init_command_by_async_with")
    assert "error" not in output.lower()
    output = run_shell("pytest -s _tests.py::test_init_command_by_await")
    assert "error" not in output.lower()
    output = run_shell("pytest -s _tests.py::test_init_command_by_init_func")
    assert "error" not in output.lower()
    shutil.move("models_2.py", "models.py")
    output = run_shell("pytest -s _tests.py::test_migrate_upgrade")
    assert "error" not in output.lower()
