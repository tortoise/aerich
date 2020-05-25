import asyncio
import os

import pytest
from tortoise import Tortoise, expand_db_url, generate_schema_for_client
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator

from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from aerich.migrate import Migrate

db_url = os.getenv("TEST_DB", "sqlite://:memory:")
tortoise_orm = {
    "connections": {"default": expand_db_url(db_url, True)},
    "apps": {
        "models": {"models": ["tests.models", "aerich.models"], "default_connection": "default",},
    },
}


@pytest.fixture(scope="function", autouse=True)
def reset_migrate():
    Migrate.upgrade_operators = []
    Migrate.downgrade_operators = []
    Migrate._upgrade_fk_m2m_index_operators = []
    Migrate._downgrade_fk_m2m_index_operators = []
    Migrate._upgrade_m2m = []
    Migrate._downgrade_m2m = []


@pytest.fixture(scope="session")
def loop():
    loop = asyncio.get_event_loop()
    return loop


@pytest.fixture(scope="session", autouse=True)
def initialize_tests(loop, request):
    tortoise_orm["connections"]["diff_models"] = "sqlite://:memory:"
    tortoise_orm["apps"]["diff_models"] = {
        "models": ["tests.diff_models"],
        "default_connection": "diff_models",
    }

    loop.run_until_complete(Tortoise.init(config=tortoise_orm, _create_db=True))
    loop.run_until_complete(
        generate_schema_for_client(Tortoise.get_connection("default"), safe=True)
    )

    client = Tortoise.get_connection("default")
    if client.schema_generator is MySQLSchemaGenerator:
        Migrate.ddl = MysqlDDL(client)
    elif client.schema_generator is SqliteSchemaGenerator:
        Migrate.ddl = SqliteDDL(client)
    elif client.schema_generator is AsyncpgSchemaGenerator:
        Migrate.ddl = PostgresDDL(client)

    request.addfinalizer(lambda: loop.run_until_complete(Tortoise._drop_databases()))
