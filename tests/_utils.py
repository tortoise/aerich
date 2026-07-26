from __future__ import annotations

import contextlib
import functools
import os
import platform
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Literal

import pytest
import tortoise
from tortoise import Tortoise, generate_schema_for_client
from tortoise.exceptions import DBConnectionError, OperationalError
from tortoise.indexes import Index

from aerich import Command

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


IS_TORTOISE_V1 = tortoise.__version__ >= "1"


async def drop_db(tortoise_orm) -> None:
    # Placing init outside the try-block(suppress) since it doesn't
    # establish connections to the DB eagerly.
    await Tortoise.init(config=tortoise_orm)
    with contextlib.suppress(DBConnectionError, OperationalError):
        await Tortoise._drop_databases()
    await Command.aclose()


async def init_db(tortoise_orm, generate_schemas=True, close_connection=True) -> None:
    await drop_db(tortoise_orm)
    await Tortoise.init(config=tortoise_orm, _create_db=True)
    if generate_schemas:
        await generate_schema_for_client(Tortoise.get_connection("default"), safe=True)
    if close_connection:
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

    @classmethod
    def check(cls, name: Literal["sqlite", "mysql", "postgres"]) -> bool:
        func = getattr(cls, f"is_{name}")
        return func()


ASSETS = Path(__file__).parent / "assets"
WINDOWS = platform.system() == "Windows"


def run_in_subprocess(command: str, capture_output=True, **kw) -> tuple[bool, str]:
    if WINDOWS:
        py = Path(sys.executable).as_posix()
        if command.startswith("aerich "):
            command = f"{py} -m " + command
        elif command.startswith(s := "python "):
            command = f"{py} " + command[len(s) :]
    if (env := kw.get("env")) is not None:
        kw["env"] = {**os.environ, **env}
    check = kw.pop("check", False)
    kw.setdefault("encoding", "utf-8")
    r = subprocess.run(shlex.split(command), capture_output=capture_output, check=check, **kw)
    ok = r.returncode == 0
    out = (r.stdout or "") if ok else (r.stderr or r.stdout or "")
    return ok, out


def run_shell(command: str, capture_output=True, **kw) -> str:
    return run_in_subprocess(command, capture_output, **kw)[1]


def _copy_file_with_symlink_target_followed(
    src: Path, target_dir: Path | str = ".", parent=ASSETS
) -> None:
    filename = src.name
    dst = Path(target_dir, "conftest.py" if filename == "conftest_.py" else filename)
    if WINDOWS:
        content = src.read_bytes()
        if content.startswith(b".."):
            shutil.copy(parent / filename, dst)
        else:
            dst.write_bytes(content)
    else:
        shutil.copy(src, dst)


@functools.cache
def get_symlink_targets(parent: Path = ASSETS) -> set[str]:
    return {i.name for i in parent.glob("*.py")}


def copy_files(*src_files: Path, target_dir: Path | str = ".", parent: Path | None = None) -> None:
    if parent is None:
        parent = src_files[0].parent
    symlink_targets = get_symlink_targets(parent)
    for src in src_files:
        if src.name in symlink_targets:
            _copy_file_with_symlink_target_followed(src, target_dir, parent)
        else:
            shutil.copy(src, target_dir)


def prepare_py_files(
    asset_name: str, assets: Path = ASSETS, suffix: str = ".py", with_testing_models: bool = False
) -> Path:
    asset_dir = assets / asset_name
    copy_files(*asset_dir.glob(f"*{suffix}"), parent=assets)
    if with_testing_models:
        test_dir = assets.parent
        copy_files(test_dir / "models_second.py", test_dir / "models.py")
        dst_dir = Path("tests")
        dst_dir.mkdir()
        dst_dir.joinpath("__init__.py").touch()
        copy_files(test_dir / "_utils.py", test_dir / "indexes.py", target_dir=dst_dir)
    return asset_dir


def copy_asset(name: str, parent: Path = ASSETS) -> None:
    asset_dir = parent / name
    symlink_targets = get_symlink_targets(parent)
    for p in asset_dir.glob("*"):
        filename = p.name
        if filename.startswith("."):
            continue
        if filename in symlink_targets:
            _copy_file_with_symlink_target_followed(p, parent=parent)
        else:
            copy_func = shutil.copytree if p.is_dir() else shutil.copyfile
            copy_func(p, "conftest.py" if p.name == "conftest_.py" else p.name)


def skip_dialect(name: Literal["sqlite", "mysql", "postgres"]) -> Callable:
    return pytest.mark.skipif(Dialect.check(name), reason=f"Skip dialect {name!r}")


def requires_dialect(
    name: Literal["sqlite", "mysql", "postgres"],
    *more: Literal["sqlite", "mysql", "postgres"],
) -> Callable:
    if more:
        vals = {name, *more}
        for dialect_name in vals:
            if Dialect.check(dialect_name):
                return pytest.mark.skipif(False, reason="")
        return pytest.mark.skipif(True, reason=f"Capability dialect not in {list(vals)}")
    return pytest.mark.skipif(not Dialect.check(name), reason=f"Capability dialect != {name}")


def requires_env(name: str) -> Callable:
    return pytest.mark.skipif(
        not (_v := os.getenv(name)) or _v.lower() not in ("1", "on", "yes", "true"),
        reason=f"Skip as os env {name!r} is not true",
    )


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


def describe_index(idx: Index) -> dict:
    return idx.describe()
