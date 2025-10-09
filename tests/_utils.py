from __future__ import annotations

import contextlib
import os
import platform
import shlex
import shutil
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Callable, Literal

from tortoise import Tortoise, generate_schema_for_client
from tortoise.contrib import test
from tortoise.contrib.test.condition import In, NotEQ
from tortoise.exceptions import DBConnectionError, OperationalError
from tortoise.indexes import Index

from aerich import Command
from aerich._compat import tortoise_version_less_than

if sys.version_info >= (3, 11):
    from contextlib import chdir
else:

    class chdir(contextlib.AbstractContextManager):  # Copied from source code of Python3.13
        """Non thread-safe context manager to change the current working directory."""

        def __init__(self, path):
            self.path = path
            self._old_cwd = []

        def __enter__(self):
            self._old_cwd.append(os.getcwd())
            os.chdir(self.path)

        def __exit__(self, *excinfo):
            os.chdir(self._old_cwd.pop())


async def drop_db(tortoise_orm) -> None:
    # Placing init outside the try-block(suppress) since it doesn't
    # establish connections to the DB eagerly.
    await Tortoise.init(config=tortoise_orm)
    with contextlib.suppress(DBConnectionError, OperationalError):
        await Tortoise._drop_databases()
    await Command.aclose()


async def init_db(tortoise_orm, generate_schemas=True) -> None:
    await drop_db(tortoise_orm)
    await Tortoise.init(config=tortoise_orm, _create_db=True)
    if generate_schemas:
        await generate_schema_for_client(Tortoise.get_connection("default"), safe=True)
    await Command.aclose()


class Dialect:
    test_db_url: str

    @classmethod
    def load_env(cls) -> None:
        if getattr(cls, "test_db_url", None) is None:
            cls.test_db_url = os.getenv("TEST_DB", "")

    @classmethod
    def is_postgres(cls) -> bool:
        cls.load_env()
        return "postgres" in cls.test_db_url

    @classmethod
    def is_mysql(cls) -> bool:
        cls.load_env()
        return "mysql" in cls.test_db_url

    @classmethod
    def is_sqlite(cls) -> bool:
        cls.load_env()
        return not cls.test_db_url or "sqlite" in cls.test_db_url


ASSETS = Path(__file__).parent / "assets"
WINDOWS = platform.system() == "Windows"


def run_in_subprocess(command: str, capture_output=True, **kw) -> tuple[bool, str]:
    if WINDOWS and command.startswith("aerich "):
        command = "python -m " + command
    r = subprocess.run(shlex.split(command), capture_output=capture_output, encoding="utf-8")
    ok = r.returncode == 0
    out = (r.stdout or "") if ok else (r.stderr or r.stdout or "")
    return ok, out


def run_shell(command: str, capture_output=True, **kw) -> str:
    return run_in_subprocess(command, capture_output, **kw)[1]


def copy_files(*src_files: Path, target_dir: Path | str = ".") -> None:
    for src in src_files:
        if src.name == "conftest_.py":
            shutil.copy(src, Path(target_dir, "conftest.py"))
        else:
            shutil.copy(src, target_dir)


def prepare_py_files(asset_name: str, assets: Path = ASSETS, suffix: str = ".py") -> Path:
    asset_dir = assets / asset_name
    copy_files(*asset_dir.glob(f"*{suffix}"))
    return asset_dir


def copy_asset(name: str, parent: Path = ASSETS) -> None:
    asset_dir = parent / name
    for p in asset_dir.glob("*"):
        if p.name.startswith("."):
            continue
        copy_func = shutil.copytree if p.is_dir() else shutil.copyfile
        copy_func(p, "conftest.py" if p.name == "conftest_.py" else p.name)


def skip_dialect(name: Literal["sqlite", "mysql", "postgres"]) -> Callable:
    return test.requireCapability("default", dialect=NotEQ(name))


def requires_dialect(
    name: Literal["sqlite", "mysql", "postgres"],
    *more: Literal["sqlite", "mysql", "postgres"],
) -> Callable:
    if more and set(more) != {name}:
        return test.requireCapability("default", dialect=In(name, *more))
    return test.requireCapability("default", dialect=name)


@contextlib.contextmanager
def tmp_daily_db(env_name="AERICH_DONT_DROP_TMP_DB") -> Generator[None]:
    me = Path(__file__)
    if not me.is_relative_to(Path.cwd()):
        shutil.copy(me, ".")
    run_in_subprocess("python db.py drop")
    ok, out = run_in_subprocess("python db.py create")
    if not ok:
        raise OperationalError(out)
    try:
        yield
    finally:
        if not os.getenv(env_name):
            ok, out = run_in_subprocess("python db.py drop")
            if not ok:
                raise OperationalError(out)


def describe_index(idx: Index) -> Index | dict:
    # tortoise-orm>=0.24 changes Index desribe to be dict
    if tortoise_version_less_than("0.24"):
        return idx
    if hasattr(idx, "describe"):
        return idx.describe()
    return idx
