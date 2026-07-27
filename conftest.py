from __future__ import annotations

import contextlib
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from tortoise import Tortoise, expand_db_url
from tortoise.backends.base_postgres.schema_generator import BasePostgresSchemaGenerator
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.contrib.test import MEMORY_SQLITE
from tortoise.exceptions import ConfigurationError

from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from aerich.migrate import Migrate
from tests._utils import chdir, init_db

db_url = os.getenv("TEST_DB", MEMORY_SQLITE)
db_url_second = os.getenv("TEST_DB_SECOND", MEMORY_SQLITE)
try:
    default_db = expand_db_url(db_url, testing=True)
except KeyError as e:
    if str(e) == "'/'":
        # Auto convert invalid path for Windows
        db_url = db_url.replace("/{/}", "{}")
        default_db = expand_db_url(db_url, testing=True)
    else:
        raise

tortoise_orm = {
    "connections": {
        "default": default_db,
        "second": expand_db_url(db_url_second, testing=True),
    },
    "apps": {
        "models": {"models": ["tests.models", "aerich.models"], "default_connection": "default"},
        "models_second": {"models": ["tests.models_second"], "default_connection": "second"},
    },
}
TEST_DIR = Path(__file__).parent / "tests"


@pytest.fixture(scope="function", autouse=True)
def reset_migrate() -> None:
    Migrate.upgrade_operators = []
    Migrate.downgrade_operators = []
    Migrate._upgrade_fk_m2m_index_operators = []
    Migrate._downgrade_fk_m2m_index_operators = []
    Migrate._upgrade_m2m = []
    Migrate._downgrade_m2m = []
    Migrate._rename_fields = {}
    Migrate._rename_models = {}


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def initialize_tests(anyio_backend):
    await init_db(tortoise_orm, close_connection=False)
    client = Tortoise.get_connection("default")
    if client.schema_generator is MySQLSchemaGenerator:
        Migrate.ddl = MysqlDDL(client)
    elif client.schema_generator is SqliteSchemaGenerator:
        Migrate.ddl = SqliteDDL(client)
    elif issubclass(client.schema_generator, BasePostgresSchemaGenerator):
        Migrate.ddl = PostgresDDL(client)
    Migrate.dialect = Migrate.ddl.DIALECT
    try:
        yield
    finally:
        with contextlib.suppress(ConfigurationError):
            await Tortoise._drop_databases()


@pytest.fixture
def tmp_work_dir(tmp_path: Path) -> Generator[Path]:
    with chdir(tmp_path):
        yield tmp_path
