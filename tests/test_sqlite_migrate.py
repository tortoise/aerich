from __future__ import annotations

import functools
import json
import os
import shlex
import shutil
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from tortoise import Tortoise

from aerich import Command, Migrate, TortoiseContext, decompress_dict, import_py_file
from aerich.models import Aerich
from aerich.utils import get_app_connection, load_tortoise_config, run_async
from tests._utils import ASSETS, WINDOWS, prepare_py_files, requires_dialect


def run_aerich(cmd: str, capture_output=False) -> subprocess.CompletedProcess:
    if not cmd.startswith("poetry") and not cmd.startswith("python"):
        if not cmd.startswith("aerich"):
            cmd = "aerich " + cmd
        if WINDOWS:
            cmd = "python -m " + cmd
    run_cmd = functools.partial(subprocess.run, shlex.split(cmd), timeout=2)
    r = run_cmd(capture_output=True, encoding="utf-8") if capture_output else run_cmd()
    return r


def run_shell(cmd: str) -> subprocess.CompletedProcess:
    envs = dict(os.environ, PYTHONPATH=".")
    return subprocess.run(shlex.split(cmd), env=envs)


def _get_empty_db() -> Path:
    if (db_file := Path("db.sqlite3")).exists():
        db_file.unlink()
    return db_file


@contextmanager
def prepare_sqlite_project(tmp_work_dir: Path) -> Generator[tuple[Path, str]]:
    prepare_py_files("sqlite_migrate")
    _get_empty_db()
    models_py = Path("models.py")
    yield models_py, models_py.read_text("utf-8")


@contextmanager
def prepare_sqlite_old_style_project(tmp_work_dir: Path) -> Generator[tuple[Path, str]]:
    asset_dir = prepare_py_files("sqlite_old_style")
    migrations_source = asset_dir / "_migrations"
    migrations_target = Path("migrations")
    _get_empty_db()
    run_aerich("init -t settings.TORTOISE_ORM")
    run_aerich("init-db")
    if migrations_target.exists():
        shutil.rmtree(migrations_target)
    shutil.copytree(migrations_source, migrations_target)

    async def init_data() -> None:
        data = json.loads(asset_dir.joinpath("data.json").read_bytes())
        await Tortoise.init(config=load_tortoise_config())
        await Aerich.bulk_create([Aerich(**d) for d in data])
        await Command.aclose()

    run_async(init_data)
    models_py = Path("models.py")
    yield models_py, models_py.read_text("utf-8")


@requires_dialect("sqlite")
def test_close_tortoise_connections_patch(tmp_work_dir: Path) -> None:
    with prepare_sqlite_project(tmp_work_dir):
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        r = run_aerich("aerich init-db")
        assert r.returncode == 0


@requires_dialect("sqlite")
def test_sqlite_migrate_alter_indexed_unique(tmp_work_dir: Path) -> None:
    with prepare_sqlite_project(tmp_work_dir) as (models_py, models_text):
        models_py.write_text(models_text.replace("db_index=False", "db_index=True"))
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        run_aerich("aerich init-db")
        r = run_shell("pytest -s _tests.py::test_allow_duplicate")
        assert r.returncode == 0
        models_py.write_text(models_text.replace("db_index=False", "unique=True"))
        r = run_aerich("aerich migrate")  # migrations/models/1_
        assert r.returncode == 0
        r = run_aerich("aerich upgrade")
        assert r.returncode == 0
        r = run_shell("pytest _tests.py::test_unique_is_true")
        assert r.returncode == 0
        models_py.write_text(models_text.replace("db_index=False", "db_index=True"))
        run_aerich("aerich migrate")  # migrations/models/2_
        run_aerich("aerich upgrade")
        r = run_shell("pytest -s _tests.py::test_allow_duplicate")
        assert r.returncode == 0


@requires_dialect("sqlite")
def test_sqlite_migrate_alter_indexed_unique_offline(tmp_work_dir: Path) -> None:
    with prepare_sqlite_project(tmp_work_dir) as (models_py, models_text):
        migration_directory = Path("migrations")
        assert not migration_directory.exists()
        models_py.write_text(models_text.replace("db_index=False", "db_index=True"))
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        run_aerich("aerich init-migrations")
        assert migration_directory.exists()
        app_migrations = migration_directory / "models"
        assert app_migrations.exists()
        created_migrations = [m for m in os.listdir(app_migrations) if m.endswith(".py")]
        assert len(created_migrations) == 1
        models_py.write_text(models_text.replace("db_index=False", "unique=True"))
        r = run_aerich("aerich migrate --offline")  # migrations/models/1_
        assert r.returncode == 0
        created_migrations = [m for m in os.listdir(app_migrations) if m.endswith(".py")]
        assert len(created_migrations) == 2, created_migrations
        models_py.write_text(models_text.replace("db_index=False", "db_index=True"))
        run_aerich("aerich migrate --offline")  # migrations/models/2_
        created_migrations = [m for m in os.listdir(app_migrations) if m.endswith(".py")]
        assert len(created_migrations) == 3, created_migrations
        run_aerich("aerich upgrade")
        r = run_shell("pytest -s _tests.py::test_allow_duplicate")
        assert r.returncode == 0


@requires_dialect("sqlite")
def test_sqlite_fix_migrations(tmp_work_dir: Path) -> None:
    with prepare_sqlite_old_style_project(tmp_work_dir) as (models_py, models_text):
        r = run_aerich("aerich upgrade")
        assert r.returncode == 1

        r = run_aerich("aerich fix-migrations")
        assert r.returncode == 0

        migrations_dir = tmp_work_dir / "migrations" / "models"

        migration_files = list(migrations_dir.glob("*.py"))

        for file in migration_files:
            imported_file = import_py_file(migrations_dir / file)

            models_state = getattr(imported_file, "MODELS_STATE", None)
            assert models_state is not None

            parsed_state = decompress_dict(models_state)
            assert isinstance(parsed_state, dict)

        r = run_aerich("aerich upgrade")
        assert r.returncode == 0

        models_py.write_text(models_text.replace("db_index=False", "unique=True"))
        r = run_aerich("aerich migrate --offline")
        assert r.returncode == 0

        r = run_aerich("aerich upgrade")
        assert r.returncode == 0

        created_migrations = migrations_dir.glob("*.py")
        assert len(list(created_migrations)) == 3, created_migrations

        message = "No migration files to update. All files are already in the correct format."
        r = run_aerich("aerich fix-migrations", capture_output=True)
        assert message in r.stdout

        for p in migrations_dir.glob("*.py"):
            p.unlink()
        if (pycache := migrations_dir / "__pycache__").exists():
            shutil.rmtree(pycache)
        r2 = run_aerich("aerich fix-migrations", capture_output=True)
        assert message not in r2.stdout
        assert "No migration file found for app 'models', nothing to do." in r2.stdout

        shutil.rmtree(migrations_dir)
        r3 = run_aerich("aerich fix-migrations", capture_output=True)
        assert message not in r3.stdout
        assert "No migration file found for app 'models', nothing to do." in r3.stdout

        asset_dir = ASSETS / "sqlite_old_style"
        migrations_source = asset_dir / "_migrations"
        shutil.copytree(migrations_source / "models", migrations_dir)

        async def delete_first_aerich():
            async with TortoiseContext():
                await Aerich.filter(version__startswith="0").delete()

        run_async(delete_first_aerich)
        r4 = run_aerich("aerich fix-migrations", capture_output=True)
        assert message not in r4.stdout
        assert "Warning: No matching record for migration" in r4.stdout

        async def remove_aerich_records():
            async with TortoiseContext():
                await Aerich.all().delete()

        run_async(remove_aerich_records)
        r5 = run_aerich("aerich fix-migrations", capture_output=True)
        assert message not in r5.stdout
        assert "Warning: Aerich table is empty." in r5.stdout

        async def drop_aerich_table():
            async with TortoiseContext():
                conn = get_app_connection(load_tortoise_config(), "models")
                sql = Migrate.drop_model("aerich")
                await conn.execute_script(sql)

        run_async(drop_aerich_table)
        r6 = run_aerich("aerich fix-migrations", capture_output=True)
        assert message not in r6.stdout
        assert "Warning: Aerich table not found." in r6.stdout


M2M_WITH_CUSTOM_THROUGH = """
    groups = fields.ManyToManyField("models.Group", through="foo_group")

class Group(Model):
    name = fields.CharField(max_length=60)

class FooGroup(Model):
    foo = fields.ForeignKeyField("models.Foo")
    group = fields.ForeignKeyField("models.Group")
    is_active = fields.BooleanField(default=False)

    class Meta:
        table = "foo_group"
"""


@requires_dialect("sqlite")
def test_sqlite_migrate(tmp_work_dir: Path) -> None:
    with prepare_sqlite_project(tmp_work_dir) as (models_py, models_text):
        MODELS = models_text
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        config_file = Path("pyproject.toml")
        modify_time = config_file.stat().st_mtime
        run_aerich("aerich init-db")
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        assert modify_time == config_file.stat().st_mtime
        r = run_shell("pytest _tests.py::test_allow_duplicate")
        assert r.returncode == 0
        # Add index
        models_py.write_text(MODELS.replace("index=False", "index=True"))
        run_aerich("aerich migrate")  # migrations/models/1_
        run_aerich("aerich upgrade")
        r = run_shell("pytest -s _tests.py::test_allow_duplicate")
        assert r.returncode == 0
        # Drop index
        models_py.write_text(MODELS)
        run_aerich("aerich migrate")  # migrations/models/2_
        run_aerich("aerich upgrade")
        r = run_shell("pytest -s _tests.py::test_allow_duplicate")
        assert r.returncode == 0
        # Add unique index
        models_py.write_text(MODELS.replace("index=False", "index=True, unique=True"))
        run_aerich("aerich migrate")  # migrations/models/3_
        run_aerich("aerich upgrade")
        r = run_shell("pytest _tests.py::test_unique_is_true")
        assert r.returncode == 0
        # Drop unique index
        models_py.write_text(MODELS)
        run_aerich("aerich migrate")  # migrations/models/4_
        run_aerich("aerich upgrade")
        r = run_shell("pytest _tests.py::test_allow_duplicate")
        assert r.returncode == 0
        # Add field with unique=True
        with models_py.open("a") as f:
            f.write("    age = fields.IntField(unique=True, default=0)")
        run_aerich("aerich migrate")  # migrations/models/5_
        run_aerich("aerich upgrade")
        r = run_shell("pytest _tests.py::test_add_unique_field")
        assert r.returncode == 0
        # Drop unique field
        models_py.write_text(MODELS)
        run_aerich("aerich migrate")  # migrations/models/6_
        run_aerich("aerich upgrade")
        r = run_shell("pytest -s _tests.py::test_drop_unique_field")
        assert r.returncode == 0

        # Initial with indexed field and then drop it
        migrations_dir = Path("migrations/models")
        shutil.rmtree(migrations_dir)
        db_file = _get_empty_db()
        models_py.write_text(MODELS + "    age = fields.IntField(db_index=True)")
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        run_aerich("aerich init-db")
        migration_file = list(migrations_dir.glob("0_*.py"))[0]
        assert "CREATE INDEX" in migration_file.read_text()
        r = run_shell("pytest _tests.py::test_with_age_field")
        assert r.returncode == 0
        models_py.write_text(MODELS)
        run_aerich("aerich migrate")
        run_aerich("aerich upgrade")
        migration_file_1 = list(migrations_dir.glob("1_*.py"))[0]
        assert "DROP INDEX" in migration_file_1.read_text()
        r = run_shell("pytest _tests.py::test_without_age_field")
        assert r.returncode == 0

        # Generate migration file in emptry directory
        db_file.unlink()
        run_aerich("aerich init-db")
        assert not db_file.exists()
        for p in migrations_dir.glob("*"):
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        run_aerich("aerich init-db")
        assert db_file.exists()

        # init without '[tool]' section in pyproject.toml
        config_file = Path("pyproject.toml")
        config_file.write_text('[project]\nname = "project"')
        run_aerich("init -t settings.TORTOISE_ORM")
        assert "[tool.aerich]" in config_file.read_text()

        # add m2m with custom model for through
        models_py.write_text(MODELS + M2M_WITH_CUSTOM_THROUGH)
        run_aerich("aerich migrate")
        run_aerich("aerich upgrade")
        migration_file_1 = list(migrations_dir.glob("1_*.py"))[0]
        assert "foo_group" in migration_file_1.read_text()
        r = run_shell("pytest _tests.py::test_m2m_with_custom_through")
        assert r.returncode == 0

        # add m2m field after init-db
        new = """
    groups = fields.ManyToManyField("models.Group", through="foo_group", related_name="users")

class Group(Model):
    name = fields.CharField(max_length=60)
        """
        _get_empty_db()
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)
        models_py.write_text(MODELS)
        run_aerich("aerich init-db")
        models_py.write_text(MODELS + new)
        run_aerich("aerich migrate")
        run_aerich("aerich upgrade")
        migration_file_1 = list(migrations_dir.glob("1_*.py"))[0]
        assert "foo_group" in migration_file_1.read_text()
        r = run_shell("pytest _tests.py::test_add_m2m_field_after_init_db")
        assert r.returncode == 0
