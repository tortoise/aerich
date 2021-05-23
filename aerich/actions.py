from pathlib import Path

from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction

from aerich.output import Output
from aerich.utils import get_models_describe, write_version_file, get_version_content_from_file

from aerich.models import Aerich

from aerich.migrate import Migrate
from tortoise import generate_schema_for_client
from tortoise.utils import get_schema_sql


async def init_db_action(
    app_name: str, location: str, connection_name: str, output: Output, safe: bool = True,
) -> bool:
    dirname = Path(location, app_name)
    Migrate.app = app_name

    try:
        dirname.mkdir(parents=True)
        output.success(f"Success create app migrate location {dirname}")
    except FileExistsError:
        output.warning(f"Inited {app_name} already, or delete {dirname} and try again.")
        return False

    async with in_transaction(connection_name) as conn:
        await generate_schema_for_client(conn, safe)

        schema = get_schema_sql(conn, safe)

        version = await Migrate.generate_version()

        await Aerich.create(
            version=version, app=app_name, content=get_models_describe(app_name),
        )

        content = {
            "upgrade": [schema],
        }
        write_version_file(Path(dirname, version), content)

        output.success(f'Success generate schema for app "{app_name}"')

    return True


async def upgrade_action(app_name: str, location: str, connection_name: str, output: Output):
    migrated = False
    Migrate.app = app_name
    Migrate.migrate_location = Path(location, app_name)
    for version_file in Migrate.get_all_version_files():
        try:
            exists = await Aerich.exists(version=version_file, app=app_name)
        except OperationalError:
            exists = False
        if not exists:
            async with in_transaction(connection_name) as conn:
                file_path = Path(Migrate.migrate_location, version_file)
                content = get_version_content_from_file(file_path)
                upgrade_query_list = content.get("upgrade")
                for upgrade_query in upgrade_query_list:
                    await conn.execute_script(upgrade_query)
                await Aerich.create(
                    version=version_file, app=app_name, content=get_models_describe(app_name),
                )
            output.success(f"Success upgrade {version_file}")
            migrated = True
    if not migrated:
        output.warning("No upgrade items found")
