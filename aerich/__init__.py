from __future__ import annotations

import os
import platform
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import TYPE_CHECKING

import tortoise
from tortoise import Tortoise, connections, generate_schema_for_client
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

from aerich.exceptions import DowngradeError
from aerich.inspectdb.mysql import InspectMySQL
from aerich.inspectdb.postgres import InspectPostgres
from aerich.inspectdb.sqlite import InspectSQLite
from aerich.migrate import MIGRATE_TEMPLATE, Migrate
from aerich.models import Aerich
from aerich.utils import (
    get_app_connection,
    get_app_connection_name,
    get_models_describe,
    import_py_file,
)

if TYPE_CHECKING:
    from tortoise import Model
    from tortoise.fields.relational import ManyToManyFieldInstance  # NOQA:F401

    from aerich.inspectdb import Inspect


def _init_asyncio_patch():
    """
    Select compatible event loop for psycopg3.

    As of Python 3.8+, the default event loop on Windows is `proactor`,
    however psycopg3 requires the old default "selector" event loop.
    See https://www.psycopg.org/psycopg3/docs/advanced/async.html
    """
    if platform.system() == "Windows":
        try:
            from asyncio import WindowsSelectorEventLoopPolicy
        except ImportError:
            pass  # Can't assign a policy which doesn't exist.
        else:
            from asyncio import get_event_loop_policy, set_event_loop_policy

            if not isinstance(get_event_loop_policy(), WindowsSelectorEventLoopPolicy):
                set_event_loop_policy(WindowsSelectorEventLoopPolicy())


def _init_tortoise_0_24_1_patch():
    # this patch is for "tortoise-orm==0.24.1" to fix:
    # https://github.com/tortoise/tortoise-orm/issues/1893
    if tortoise.__version__ != "0.24.1":
        return
    from tortoise.backends.base.schema_generator import BaseSchemaGenerator, cast, re

    def _get_m2m_tables(
        self, model: type[Model], db_table: str, safe: bool, models_tables: list[str]
    ) -> list[str]:  # Copied from tortoise-orm
        m2m_tables_for_create = []
        for m2m_field in model._meta.m2m_fields:
            field_object = cast("ManyToManyFieldInstance", model._meta.fields_map[m2m_field])
            if field_object._generated or field_object.through in models_tables:
                continue
            backward_key, forward_key = field_object.backward_key, field_object.forward_key
            if field_object.db_constraint:
                backward_fk = self._create_fk_string(
                    "",
                    backward_key,
                    db_table,
                    model._meta.db_pk_column,
                    field_object.on_delete,
                    "",
                )
                forward_fk = self._create_fk_string(
                    "",
                    forward_key,
                    field_object.related_model._meta.db_table,
                    field_object.related_model._meta.db_pk_column,
                    field_object.on_delete,
                    "",
                )
            else:
                backward_fk = forward_fk = ""
            exists = "IF NOT EXISTS " if safe else ""
            through_table_name = field_object.through
            backward_type = self._get_pk_field_sql_type(model._meta.pk)
            forward_type = self._get_pk_field_sql_type(field_object.related_model._meta.pk)
            comment = ""
            if desc := field_object.description:
                comment = self._table_comment_generator(table=through_table_name, comment=desc)
            m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
                exists=exists,
                table_name=through_table_name,
                backward_fk=backward_fk,
                forward_fk=forward_fk,
                backward_key=backward_key,
                backward_type=backward_type,
                forward_key=forward_key,
                forward_type=forward_type,
                extra=self._table_generate_extra(table=field_object.through),
                comment=comment,
            )
            if not field_object.db_constraint:
                m2m_create_string = m2m_create_string.replace(
                    """,
    ,
    """,
                    "",
                )  # may have better way
            m2m_create_string += self._post_table_hook()
            if field_object.create_unique_index:
                unique_index_create_sql = self._get_unique_index_sql(
                    exists, through_table_name, [backward_key, forward_key]
                )
                if unique_index_create_sql.endswith(";"):
                    m2m_create_string += "\n" + unique_index_create_sql
                else:
                    lines = m2m_create_string.splitlines()
                    lines[-2] += ","
                    indent = m.group() if (m := re.match(r"\s+", lines[-2])) else ""
                    lines.insert(-1, indent + unique_index_create_sql)
                    m2m_create_string = "\n".join(lines)
            m2m_tables_for_create.append(m2m_create_string)
        return m2m_tables_for_create

    BaseSchemaGenerator._get_m2m_tables = _get_m2m_tables


_init_asyncio_patch()
_init_tortoise_0_24_1_patch()


class Command(AbstractAsyncContextManager):
    def __init__(
        self,
        tortoise_config: dict,
        app: str = "models",
        location: str = "./migrations",
    ) -> None:
        self.tortoise_config = tortoise_config
        self.app = app
        self.location = location
        Migrate.app = app

    async def init(self) -> None:
        await Migrate.init(self.tortoise_config, self.app, self.location)

    async def __aenter__(self) -> Command:
        await self.init()
        return self

    async def close(self) -> None:
        await connections.close_all()

    async def __aexit__(self, *args, **kw) -> None:
        await self.close()

    async def _upgrade(self, conn, version_file, fake: bool = False) -> None:
        file_path = Path(Migrate.migrate_location, version_file)
        m = import_py_file(file_path)
        upgrade = m.upgrade
        if not fake:
            await conn.execute_script(await upgrade(conn))
        await Aerich.create(
            version=version_file,
            app=self.app,
            content=get_models_describe(self.app),
        )

    async def upgrade(self, run_in_transaction: bool = True, fake: bool = False) -> list[str]:
        migrated = []
        for version_file in Migrate.get_all_version_files():
            try:
                exists = await Aerich.exists(version=version_file, app=self.app)
            except OperationalError:
                exists = False
            if not exists:
                app_conn_name = get_app_connection_name(self.tortoise_config, self.app)
                if run_in_transaction:
                    async with in_transaction(app_conn_name) as conn:
                        await self._upgrade(conn, version_file, fake=fake)
                else:
                    app_conn = get_app_connection(self.tortoise_config, self.app)
                    await self._upgrade(app_conn, version_file, fake=fake)
                migrated.append(version_file)
        return migrated

    async def downgrade(self, version: int, delete: bool, fake: bool = False) -> list[str]:
        ret: list[str] = []
        if version == -1:
            specified_version = await Migrate.get_last_version()
        else:
            specified_version = await Aerich.filter(
                app=self.app, version__startswith=f"{version}_"
            ).first()
        if not specified_version:
            raise DowngradeError("No specified version found")
        if version == -1:
            versions = [specified_version]
        else:
            versions = await Aerich.filter(app=self.app, pk__gte=specified_version.pk)
        for version_obj in versions:
            file = version_obj.version
            async with in_transaction(
                get_app_connection_name(self.tortoise_config, self.app)
            ) as conn:
                file_path = Path(Migrate.migrate_location, file)
                m = import_py_file(file_path)
                downgrade = m.downgrade
                downgrade_sql = await downgrade(conn)
                if not downgrade_sql.strip():
                    raise DowngradeError("No downgrade items found")
                if not fake:
                    await conn.execute_script(downgrade_sql)
                await version_obj.delete()
                if delete:
                    os.unlink(file_path)
                ret.append(file)
        return ret

    async def heads(self) -> list[str]:
        ret = []
        versions = Migrate.get_all_version_files()
        for version in versions:
            if not await Aerich.exists(version=version, app=self.app):
                ret.append(version)
        return ret

    async def history(self) -> list[str]:
        versions = Migrate.get_all_version_files()
        return [version for version in versions]

    async def inspectdb(self, tables: list[str] | None = None) -> str:
        connection = get_app_connection(self.tortoise_config, self.app)
        dialect = connection.schema_generator.DIALECT
        if dialect == "mysql":
            cls: type[Inspect] = InspectMySQL
        elif dialect == "postgres":
            cls = InspectPostgres
        elif dialect == "sqlite":
            cls = InspectSQLite
        else:
            raise NotImplementedError(f"{dialect} is not supported")
        inspect = cls(connection, tables)
        return await inspect.inspect()

    async def migrate(self, name: str = "update", empty: bool = False) -> str:
        return await Migrate.migrate(name, empty)

    async def init_db(self, safe: bool) -> None:
        location = self.location
        app = self.app
        dirname = Path(location, app)
        if not dirname.exists():
            dirname.mkdir(parents=True)
        else:
            # If directory is empty, go ahead, otherwise raise FileExistsError
            for unexpected_file in dirname.glob("*"):
                raise FileExistsError(str(unexpected_file))

        await Tortoise.init(config=self.tortoise_config)
        connection = get_app_connection(self.tortoise_config, app)
        await generate_schema_for_client(connection, safe)

        schema = get_schema_sql(connection, safe)

        version = await Migrate.generate_version()
        await Aerich.create(
            version=version,
            app=app,
            content=get_models_describe(app),
        )
        version_file = Path(dirname, version)
        content = MIGRATE_TEMPLATE.format(upgrade_sql=schema, downgrade_sql="")
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)
