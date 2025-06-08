from __future__ import annotations

import os
import shutil
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from aerich._compat import tomllib
from tests._utils import chdir, run_shell


@pytest.fixture
def tmp_work_dir(tmp_path: Path) -> Generator[Path]:
    with chdir(tmp_path):
        yield tmp_path


@pytest.fixture
def new_project(tmp_work_dir: Path) -> Generator[Path]:
    asset_dir = Path(__file__).parent / "assets" / "migrate_no_input"
    for file in asset_dir.glob("*.py"):
        shutil.copy(file, file.name)
    run_shell("aerich init -t settings.TORTOISE_ORM", capture_output=False)
    run_shell("aerich init-db", capture_output=False)
    yield tmp_work_dir


def test_empty_migrate_with_no_input(new_project: Path):
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
async def project_with_unapplied_migrations(new_project: Path):
    models_py = Path("models.py")
    text = models_py.read_text()
    if "age" not in text:
        models_py.write_text(text + "    age=fields.IntField()\n")
    run_shell("aerich migrate", cwd=new_project)


def test_migrate_with_same_version_file_exists(project_with_unapplied_migrations):
    # CliRunner change the entire interpreter state, so run it in subprocess
    output = run_shell("pytest _tests.py")
    assert "1 passed" in output


def test_missing_aerich_models(tmp_path: Path):
    asset_dir = Path(__file__).parent / "assets" / "missing_aerich_models"
    with chdir(tmp_path):
        for file in asset_dir.glob("*.py"):
            shutil.copy(file, file.name)
        run_shell("aerich init -t settings.TORTOISE_ORM_NO_AERICH_MODELS", capture_output=False)
        output = run_shell("aerich init-db")
        assert "You have to add 'aerich.models' in the models of your tortoise config" in output
        output = run_shell("aerich migrate")
        assert "need to run `aerich init-db` first" in output
        output = run_shell("aerich upgrade")
        assert "need to run `aerich init-db` first" in output
        Path("migrations", "models").mkdir()
        output = run_shell("aerich migrate")
        assert "You have to add 'aerich.models' in the models of your tortoise config" in output
        output = run_shell("aerich upgrade")
        assert "You have to add 'aerich.models' in the models of your tortoise config" in output


def test_aerich_init(tmp_work_dir: Path):
    asset_dir = Path(__file__).parent / "assets" / "missing_aerich_models"
    for file in ("settings.py", "models.py"):
        shutil.copy(asset_dir / file, file)
    toml_file = Path("pyproject.toml")
    # init without pyproject.toml
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert toml_file.exists()
    assert f"Success writing aerich config to {toml_file}" in output
    doc: dict = tomllib.loads(toml_file.read_text("utf-8"))
    assert doc["tool"]["aerich"]["tortoise_orm"] == "settings.TORTOISE_ORM"
    modified_at = toml_file.stat().st_mtime
    # init again does not changed the modify time of config file
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert f"Aerich config {toml_file} already inited." in output
    assert modified_at == toml_file.stat().st_mtime
    # modify without comment line in config file
    output = run_shell("aerich init -t settings.TORTOISE_ORM_NO_AERICH_MODELS")
    assert f"Success writing aerich config to {toml_file}" in output
    # init will not remove comment line in config file
    comment_line = "# This is a comment line."
    with toml_file.open("a") as f:
        f.writelines([os.linesep, comment_line + os.linesep])
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert f"Success writing aerich config to {toml_file}" in output
    assert comment_line in toml_file.read_text("utf-8")
    toml_file.write_text(comment_line, encoding="utf-8")
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert f"Success writing aerich config to {toml_file}" in output
    assert comment_line in toml_file.read_text("utf-8")
