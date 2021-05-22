from pathlib import Path

from aerich.output import Output
from aerich.utils import get_models_describe, write_version_file

from aerich.models import Aerich

from aerich.migrate import Migrate
from tortoise import generate_schema_for_client, BaseDBAsyncClient
from tortoise.utils import get_schema_sql


async def init_db_action(
    app_name: str, location: str, connection: BaseDBAsyncClient, output: Output, safe: bool = True,
) -> bool:
    dirname = Path(location, app_name)

    try:
        dirname.mkdir(parents=True)
        output.success(f"Success create app migrate location {dirname}")
    except FileExistsError:
        output.warning(f"Inited {app_name} already, or delete {dirname} and try again.")
        return False

    await generate_schema_for_client(connection, safe)

    schema = get_schema_sql(connection, safe)

    Migrate.app = app_name

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
