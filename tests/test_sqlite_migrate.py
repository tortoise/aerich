from __future__ import annotations

import contextlib
import os
import platform
import shlex
import shutil
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from aerich import decompress_dict, import_py_file
from tests._utils import Dialect, chdir, copy_files


def run_aerich(cmd: str) -> subprocess.CompletedProcess | None:
    if not cmd.startswith("poetry") and not cmd.startswith("python"):
        if not cmd.startswith("aerich"):
            cmd = "aerich " + cmd
        if platform.system() == "Windows":
            cmd = "python -m " + cmd
    r = None
    with contextlib.suppress(subprocess.TimeoutExpired):
        r = subprocess.run(shlex.split(cmd), timeout=2)
    return r


def run_shell(cmd: str) -> subprocess.CompletedProcess:
    envs = dict(os.environ, PYTHONPATH=".")
    return subprocess.run(shlex.split(cmd), env=envs)


def _get_empty_db() -> Path:
    if (db_file := Path("db.sqlite3")).exists():
        db_file.unlink()
    return db_file


@contextmanager
def prepare_sqlite_project(tmp_path: Path) -> Generator[tuple[Path, str]]:
    test_dir = Path(__file__).parent
    asset_dir = test_dir / "assets" / "sqlite_migrate"
    with chdir(tmp_path):
        files = ("models.py", "settings.py", "_tests.py")
        copy_files(*(asset_dir / f for f in files), target_dir=Path())
        models_py, settings_py, test_py = (Path(f) for f in files)
        copy_files(asset_dir / "conftest_.py", target_dir=Path("conftest.py"))
        _get_empty_db()
        yield models_py, models_py.read_text("utf-8")


@contextmanager
def prepare_sqlite_old_style_project(tmp_path: Path) -> Generator[tuple[Path, str]]:
    test_dir = Path(__file__).parent
    asset_dir = test_dir / "assets" / "sqlite_old_style"
    with chdir(tmp_path):
        files = ("models.py", "settings.py", "_tests.py", "pyproject.toml", "example_db.sqlite3")
        copy_files(*(asset_dir / f for f in files), target_dir=Path())
        models_py = Path(files[0])
        copy_files(asset_dir / "conftest_.py", target_dir=Path("conftest.py"))

        migrations_source = asset_dir / "_migrations"
        migrations_target = Path("migrations")
        if migrations_source.exists():
            if migrations_target.exists():
                shutil.rmtree(migrations_target)
            shutil.copytree(migrations_source, migrations_target)

        _get_empty_db()
        yield models_py, models_py.read_text("utf-8")


def test_close_tortoise_connections_patch(tmp_path: Path) -> None:
    if not Dialect.is_sqlite():
        return
    with prepare_sqlite_project(tmp_path) as (models_py, models_text):
        run_aerich("aerich init -t settings.TORTOISE_ORM")
        r = run_aerich("aerich init-db")
        assert r is not None


def test_sqlite_migrate_alter_indexed_unique(tmp_path: Path) -> None:
    if not Dialect.is_sqlite():
        return
    with prepare_sqlite_project(tmp_path) as (models_py, models_text):
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


def test_sqlite_migrate_alter_indexed_unique_offline(tmp_path: Path) -> None:
    if not Dialect.is_sqlite():
        return
    with prepare_sqlite_project(tmp_path) as (models_py, models_text):
        migration_directory = tmp_path / "migrations"
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
        r = run_aerich("aerich migrate")  # migrations/models/1_
        assert r.returncode == 0
        created_migrations = [m for m in os.listdir(app_migrations) if m.endswith(".py")]
        assert len(created_migrations) == 2, created_migrations
        models_py.write_text(models_text.replace("db_index=False", "db_index=True"))
        run_aerich("aerich migrate")  # migrations/models/2_
        created_migrations = [m for m in os.listdir(app_migrations) if m.endswith(".py")]
        assert len(created_migrations) == 3, created_migrations
        run_aerich("aerich upgrade")
        r = run_shell("pytest -s _tests.py::test_allow_duplicate")
        assert r.returncode == 0


def test_sqlite_fix_migrations(tmp_path: Path) -> None:
    if not Dialect.is_sqlite():
        return
    with prepare_sqlite_old_style_project(tmp_path) as (models_py, models_text):
        r = run_aerich("aerich upgrade")
        assert r.returncode == 1

        r = run_aerich("aerich fix-migrations")
        assert r.returncode == 0

        migrations_dir = tmp_path / "migrations" / "models"

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
        r = run_aerich("aerich migrate")
        assert r.returncode == 0

        r = run_aerich("aerich upgrade")
        assert r.returncode == 0

        created_migrations = migrations_dir.glob("*.py")
        assert len(list(created_migrations)) == 3, created_migrations


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


def test_sqlite_migrate(tmp_path: Path) -> None:
    if not Dialect.is_sqlite():
        return
    with prepare_sqlite_project(tmp_path) as (models_py, models_text):
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
