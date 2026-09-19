from __future__ import annotations

from pathlib import Path

from tortoise import Tortoise

from aerich import Command
from aerich.migrate import Migrate
from aerich.utils import get_app_connection, split_sql_statements
from conftest import tortoise_orm
from tests._utils import drop_db, init_db, requires_dialect


def test_split_sql_statements() -> None:
    script = "CREATE INDEX CONCURRENTLY idx_a ON t (a); DROP INDEX CONCURRENTLY idx_b;"
    assert split_sql_statements(script) == [
        "CREATE INDEX CONCURRENTLY idx_a ON t (a)",
        "DROP INDEX CONCURRENTLY idx_b",
    ]
    assert split_sql_statements("  ;  ; ") == []
    assert split_sql_statements("") == []
    assert split_sql_statements("SELECT 1") == ["SELECT 1"]


@requires_dialect("postgres")
async def test_upgrade_runs_concurrently_statements_outside_transaction(tmp_work_dir: Path) -> None:
    """A migration with RUN_IN_TRANSACTION = False and more than one
    CREATE/DROP INDEX CONCURRENTLY statement must run each statement
    separately, or PostgreSQL implicitly wraps the whole multi-statement
    script in a transaction and every such statement after the first
    fails with "... cannot run inside a transaction block", see #467.
    """
    await init_db(tortoise_orm, generate_schemas=True, close_connection=False)
    try:
        conn = Tortoise.get_connection("default")
        await conn.execute_script(
            "DROP TABLE IF EXISTS run_in_transaction_t; "
            "CREATE TABLE run_in_transaction_t (id serial primary key, a int, b int);"
        )

        migrations_dir = tmp_work_dir / "migrations" / "models"
        migrations_dir.mkdir(parents=True)
        Migrate.migrate_location = migrations_dir
        version_file = "0_test.py"
        (migrations_dir / version_file).write_text(
            "from tortoise import BaseDBAsyncClient\n\n"
            "RUN_IN_TRANSACTION = False\n\n\n"
            "async def upgrade(db: BaseDBAsyncClient) -> str:\n"
            "    return (\n"
            '        "CREATE INDEX CONCURRENTLY run_in_transaction_idx_a '
            'ON run_in_transaction_t (a); "\n'
            '        "CREATE INDEX CONCURRENTLY run_in_transaction_idx_b '
            'ON run_in_transaction_t (b);"\n'
            "    )\n\n\n"
            "async def downgrade(db: BaseDBAsyncClient) -> str:\n"
            '    return ""\n'
        )

        command = Command(tortoise_orm)
        app_conn = get_app_connection(tortoise_orm, "models")
        await command._upgrade(app_conn, version_file, run_in_transaction=False)

        rows = await conn.execute_query_dict(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'run_in_transaction_t' "
            "AND indexname LIKE 'run_in_transaction_idx_%' ORDER BY indexname"
        )
        assert [r["indexname"] for r in rows] == [
            "run_in_transaction_idx_a",
            "run_in_transaction_idx_b",
        ]
    finally:
        await drop_db(tortoise_orm)
