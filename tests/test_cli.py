from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from asyncclick.testing import CliRunner

from aerich.cli import cli
from aerich.migrate import Migrate
from tests._utils import chdir

MODEL_TEXT = """from tortoise import Model, fields
class NewModel(Model):
    name = fields.CharField(10)
"""
SETTINGS = """TORTOISE_ORM = {
    "connections": {"default": 'sqlite://db.sqlite3'},
    "apps": {"models": {"models": ["models", "aerich.models"]},},
}"""


@pytest.fixture
def new_project(tmp_path):
    with chdir(tmp_path):
        Path("models.py").write_text(MODEL_TEXT)
        Path("settings.py").write_text(SETTINGS)
        yield


async def test_migrate_command_output(mocker, new_project) -> None:
    runner = CliRunner()
    result = await runner.invoke(cli, ["init", "-t", "settings.TORTOISE_ORM"])
    assert not result.exception
    result = await runner.invoke(cli, ["init-db"])
    assert not result.exception
    result = await runner.invoke(cli, ["migrate"])
    assert not result.exception
    assert "No changes detected" in result.output
    result = await runner.invoke(cli, ["migrate", "--empty"], input="False\n")
    assert not result.exception
    assert "success" in result.output.lower()
    empty_migration_files = list(Path(Migrate.migrate_location).glob("1_*.py"))
    assert len(empty_migration_files) == 1
    await anyio.Path("models.py").write_text(MODEL_TEXT + "    age=fields.IntField()\n")
    await anyio.lowlevel.checkpoint()
    result = await runner.invoke(cli, ["migrate", "--empty"], input="False\n")
    assert not result.exception
    warning_msg = (
        "Aborted! You may need to run `aerich heads` to list avaliable unapplied migrations."
    )
    assert warning_msg in result.output
    assert list(Path(Migrate.migrate_location).glob("1_*.py")) == empty_migration_files
    await anyio.sleep(1)  # ensure new migration filename generated.
    result = await runner.invoke(cli, ["migrate", "--empty"], input="True\n")
    new_empty_migration_files = list(Path(Migrate.migrate_location).glob("1_*.py"))
    assert len(new_empty_migration_files) == 1
    assert empty_migration_files != new_empty_migration_files
    result = await runner.invoke(cli, ["migrate"], input="False\n")
    assert not result.exception
    assert warning_msg in result.output
