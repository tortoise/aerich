from __future__ import annotations

from pathlib import Path

import pytest
from asyncclick.testing import CliRunner

from aerich.cli import cli
from aerich.migrate import Migrate


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_migrate():
    runner = CliRunner()
    # Default to abort without deleting previous generated migration files
    result = await runner.invoke(cli, ["migrate"], input="\n")
    assert not result.exception
    assert "it" in result.output
    warning_msg = (
        "Aborted! You may need to run `aerich heads` to list avaliable unapplied migrations."
    )
    assert warning_msg in result.output
    migrate_dir = Path(Migrate.migrate_location)
    extra_migration_file = migrate_dir.joinpath("1_datetime_update.py")
    extra_migration_file.touch()
    pre_migration_files = list(migrate_dir.glob("1_*.py"))
    updated_at_0 = pre_migration_files[0].stat().st_mtime
    # Delete migration files that with same version num when explicit input True
    result = await runner.invoke(cli, ["migrate"], input="True\n")
    assert not result.exception
    assert "them" in result.output
    assert all(i.name in result.output for i in pre_migration_files)
    assert not extra_migration_file.exists()
    new_migration_files = list(migrate_dir.glob("1_*.py"))
    assert len(new_migration_files) == 1
    updated_at = new_migration_files[0].stat().st_mtime
    assert updated_at > updated_at_0
    # Delete migration files without ask for prompt when --no-input passed
    result = await runner.invoke(cli, ["migrate", "--no-input"])
    assert not result.exception
    assert "them" not in result.output and "it" not in result.output
    latest_migration_files = list(migrate_dir.glob("1_*.py"))
    assert len(latest_migration_files) == 1
    updated_at_2 = latest_migration_files[0].stat().st_mtime
    assert updated_at_2 > updated_at
