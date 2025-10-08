from __future__ import annotations

import os
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from aerich._compat import tomllib
from aerich.cli import inspectdb, upgrade
from tests._utils import chdir, prepare_py_files, requires_dialect, run_shell


@pytest.fixture
def new_project(tmp_work_dir: Path) -> Generator[Path]:
    prepare_py_files("migrate_no_input")
    run_shell("aerich init -t settings.TORTOISE_ORM", capture_output=False)
    run_shell("aerich init-db", capture_output=False)
    yield tmp_work_dir


def test_empty_migrate_with_no_input(new_project: Path) -> None:
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
async def project_with_unapplied_migrations(new_project: Path) -> None:
    models_py = Path("models.py")
    text = models_py.read_text()
    if "age" not in text:
        models_py.write_text(text + "    age=fields.IntField()\n")
    run_shell("aerich migrate", cwd=new_project)


def test_migrate_with_same_version_file_exists(project_with_unapplied_migrations) -> None:
    # CliRunner change the entire interpreter state, so run it in subprocess
    output = run_shell("pytest _tests.py")
    assert "1 passed" in output


@requires_dialect("sqlite")
@pytest.mark.usefixtures("tmp_work_dir")
def test_auto_add_aerich_models() -> None:
    prepare_py_files("missing_aerich_models")
    output = run_shell("aerich init -t settings.TORTOISE_ORM_NO_AERICH_MODELS")
    assert "Success writing aerich config to pyproject.toml" in output
    output = run_shell("aerich init-db")
    db = "db.sqlite3"
    assert f'Success writing schemas to database "{db}"' in output
    with open("models.py", "a+") as f:
        f.write("    b = fields.IntField(null=True)\n")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output


@requires_dialect("sqlite")
@pytest.mark.usefixtures("tmp_work_dir")
def test_missing_aerich_models() -> None:
    prepare_py_files("missing_aerich_models")
    output = run_shell("aerich init -t settings.TORTOISE_ORM_MULTI_APPS_WITHOUT_AERICH_MODELS")
    assert "Success writing aerich config to pyproject.toml" in output
    output = run_shell("aerich init-db")
    assert "You have to add 'aerich.models' in the models of your tortoise config" in output

    output = run_shell("aerich init -t settings.TORTOISE_ORM_MULTI_APPS")
    assert "Success writing aerich config to pyproject.toml" in output
    output = run_shell("aerich migrate")
    assert "need to run `aerich init-db` first" in output
    output = run_shell("aerich upgrade")
    assert "need to run `aerich init-db` first" in output

    output = run_shell("aerich init-db")
    assert "Success" in output
    output = run_shell("aerich init -t settings.TORTOISE_ORM_MULTI_APPS_WITHOUT_AERICH_MODELS")
    assert "Success writing aerich config to pyproject.toml" in output
    output = run_shell("aerich migrate")
    assert "You have to add 'aerich.models' in the models of your tortoise config" in output
    output = run_shell("aerich upgrade")
    assert "You have to add 'aerich.models' in the models of your tortoise config" in output

    output = run_shell("aerich init -t settings.TORTOISE_ORM_MULTI_APPS")
    assert "Success" in output
    with open("models.py", "a+") as f:
        f.write("    b = fields.IntField(null=True)\n")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output


@pytest.mark.usefixtures("tmp_work_dir")
def test_aerich_init() -> None:
    prepare_py_files("missing_aerich_models")
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
    doc = tomllib.loads(toml_file.read_text("utf-8"))
    assert doc["tool"]["aerich"]["tortoise_orm"] == "settings.TORTOISE_ORM_NO_AERICH_MODELS"
    # init will not remove comment line in config file
    comment_line = "# This is a comment line."
    with toml_file.open("a", encoding="utf-8") as f:
        f.writelines([os.linesep, comment_line + os.linesep])
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert f"Success writing aerich config to {toml_file}" in output
    text = toml_file.read_text("utf-8")
    assert comment_line in text
    doc = tomllib.loads(text)
    assert doc["tool"]["aerich"]["tortoise_orm"] == "settings.TORTOISE_ORM"
    # In line comment will not remove either
    content = os.linesep.join([comment_line, "[tool.mypy]", "pretty=true # comment-2"])
    toml_file.write_text(content, encoding="utf-8")
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert f"Success writing aerich config to {toml_file}" in output
    text = toml_file.read_text("utf-8")
    assert comment_line in text
    assert "comment-2" in text
    doc = tomllib.loads(text)
    assert doc["tool"]["aerich"]["tortoise_orm"] == "settings.TORTOISE_ORM"


def test_help(tmp_path):
    output = run_shell("aerich --help")
    assert output == run_shell("aerich -h")
    assert str(upgrade.help) in output
    assert "--fake" not in output
    output = run_shell("aerich upgrade --help")
    assert output == run_shell("aerich upgrade -h")
    assert str(upgrade.help) in output
    assert "--fake" in output
    with chdir(tmp_path):
        output = run_shell(f"aerich {inspectdb.name} --help")
        assert output == run_shell(f"aerich {inspectdb.name} -h")
        assert str(inspectdb.help) in output
        assert "--table" in output
