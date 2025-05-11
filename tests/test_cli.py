from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from tests._utils import chdir, run_shell


@pytest.fixture
def new_project(tmp_path):
    asset_dir = Path(__file__).parent / "assets" / "migrate_no_input"
    with chdir(tmp_path):
        for file in asset_dir.glob("*.py"):
            shutil.copy(file, file.name)
        run_shell("aerich init -t settings.TORTOISE_ORM", capture_output=False)
        run_shell("aerich init-db", capture_output=False)
        yield tmp_path


def test_empty_migrate_with_no_input(mocker, new_project) -> None:
    output = run_shell("aerich migrate", cwd=new_project)
    assert "No changes detected" in output
    output = run_shell("aerich migrate --empty", cwd=new_project)
    assert "Success" in output
    migrate_dir = Path("migrations/models")
    empty_migration_files = list(migrate_dir.glob("1_*.py"))
    assert len(empty_migration_files) == 1
    time.sleep(1)  # ensure new migration filename generated.
    run_shell("aerich migrate --empty --no-input", cwd=new_project)
    new_empty_migration_files = list(migrate_dir.glob("1_*.py"))
    assert len(new_empty_migration_files) == 1
    assert empty_migration_files != new_empty_migration_files


@pytest.fixture
async def project_with_unapplied_migrations(new_project):
    models_py = Path("models.py")
    text = models_py.read_text()
    if "age" not in text:
        models_py.write_text(text + "    age=fields.IntField()\n")
    run_shell("aerich migrate", cwd=new_project)


def test_migrate_with_same_version_file_exists(project_with_unapplied_migrations) -> None:
    # CliRunner change the entire interpreter state, so run it in subprocess
    output = run_shell("pytest _tests.py")
    assert "1 passed" in output
