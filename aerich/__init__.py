import os
from pathlib import Path
from typing import List

from tortoise import Tortoise, generate_schema_for_client
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

from aerich.exceptions import DowngradeError
from aerich.inspectdb import InspectDb
from aerich.migrate import Migrate
from aerich.models import Aerich
from aerich.utils import (
    get_app_connection,
    get_app_connection_name,
    get_models_describe,
    get_version_content_from_file,
    write_version_file,
)


class Command:
    def __init__(
        self,
        tortoise_config: dict,
        app: str = "models",
        location: str = "./migrations",
    ):
        self.tortoise_config = tortoise_config
        self.app = app
        self.location = location
        Migrate.app = app

    async def init(self):
        await Migrate.init(self.tortoise_config, self.app, self.location)

    async def upgrade(self):
        migrated = []
        for version_file in Migrate.get_all_version_files():
            try:
                exists = await Aerich.exists(version=version_file, app=self.app)
            except OperationalError:
                exists = False
            if not exists:
                async with in_transaction(
                    get_app_connection_name(self.tortoise_config, self.app)
                ) as conn:
                    file_path = Path(Migrate.migrate_location, version_file)
                    content = get_version_content_from_file(file_path)
                    upgrade_query_list = content.get("upgrade")
                    for upgrade_query in upgrade_query_list:
                        await conn.execute_script(upgrade_query)
                    await Aerich.create(
                        version=version_file,
                        app=self.app,
                        content=get_models_describe(self.app),
                    )
                migrated.append(version_file)
        return migrated

    async def downgrade(self, version: int, delete: bool):
        ret = []
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
        for version in versions:
            file = version.version
            async with in_transaction(
                get_app_connection_name(self.tortoise_config, self.app)
            ) as conn:
                file_path = Path(Migrate.migrate_location, file)
                content = get_version_content_from_file(file_path)
                downgrade_query_list = content.get("downgrade")
                if not downgrade_query_list:
                    raise DowngradeError("No downgrade items found")
                for downgrade_query in downgrade_query_list:
                    await conn.execute_query(downgrade_query)
                await version.delete()
                if delete:
                    os.unlink(file_path)
                ret.append(file)
        return ret

    async def heads(self):
        ret = []
        versions = Migrate.get_all_version_files()
        for version in versions:
            if not await Aerich.exists(version=version, app=self.app):
                ret.append(version)
        return ret

    async def history(self):
        ret = []
        versions = Migrate.get_all_version_files()
        for version in versions:
            ret.append(version)
        return ret

    async def inspectdb(self, tables: List[str]):
        connection = get_app_connection(self.tortoise_config, self.app)
        inspect = InspectDb(connection, tables)
        await inspect.inspect()

    async def migrate(self, name: str = "update"):
        return await Migrate.migrate(name)

    async def init_db(self, safe: bool):
        location = self.location
        app = self.app
        dirname = Path(location, app)
        dirname.mkdir(parents=True)

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
        content = {
            "upgrade": [schema],
        }
        write_version_file(Path(dirname, version), content)
