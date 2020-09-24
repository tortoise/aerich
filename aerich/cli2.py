import asyncio
import functools
import json
import os
import sys

from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

from aerich.models import Aerich
from tortoise import Tortoise, generate_schema_for_client
import typer
from configparser import ConfigParser
from typer import Context

from aerich.migrate import Migrate
from aerich.typer_utils import get_app_connection, get_app_connection_name, get_tortoise_config
app = typer.Typer()
parser = ConfigParser()

def close_db(func):
    async def close_db_inner(*args, **kwargs):
        result = await func(*args, **kwargs)
        await Tortoise.close_connections()
        return result
    @functools.wraps(func)
    def close_db_inner2(*args, **kwargs):
        return asyncio.run(close_db_inner(*args, **kwargs))
    return close_db_inner2



async def connect_tortoise(ctx:Context):
    app = ctx.obj["app"]
    config = ctx.obj["config"]
    location = ctx.obj['location']
    await Migrate.init_with_old_models(config, app, location)
    return app,config,location

@app.command()
@close_db
async def init(ctx: typer.Context, tortoise_orm: str = typer.Option(..., "--tortoise-orm", "-t",
                                                                    help="Tortoise-ORM config module dict variable, like settings.TORTOISE_ORM.", ),
               location: str = typer.Option("./migrations", help="Migrate store location."),
               ):
    """
    Init config file and generate root migrate location.
    """
    config_file = ctx.obj["config_file"]
    name = ctx.obj["name"]
    if os.path.exists(config_file):
        return typer.secho("You have inited", fg=typer.colors.YELLOW)
    parser.add_section(name)
    parser.set(name, "tortoise_orm", tortoise_orm)
    parser.set(name, "location", location)
    with open(config_file, "w", encoding="utf-8") as f:
        parser.write(f)
    if not os.path.isdir(location):
        os.mkdir(location)
    typer.secho(f"Success create migrate location {location}", fg=typer.colors.GREEN)
    typer.secho(f"Success generate config file {config_file}", fg=typer.colors.GREEN)


@app.command()
@close_db
async def migrate(ctx: typer.Context, name: str = typer.Option("update", help="Migrate name.")):
    """
    Generate migrate changes file.
    """
    app,config,location=await connect_tortoise(ctx)
    ret = await Migrate.migrate(name)
    if not ret:
        return typer.secho("No changes detected", fg=typer.colors.YELLOW)
    Migrate.write_old_models(config, app, location)
    typer.secho(f"Success migrate {ret}", fg=typer.colors.GREEN)


# todo: @click.version_option(__version__, "-V", "--version")
@app.callback()
@close_db
async def cli(ctx: Context, config: str = typer.Option("aerich.ini", "--config", "-c", help="Config file.", ),
              app: str = typer.Option(None, help="Tortoise-ORM app name."),
              name: str = typer.Option("aerich", "--name", "-n",
                                       help="Name of section in .ini file to use for aerich config.", )):
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config
    ctx.obj["name"] = name
    invoked_subcommand = ctx.invoked_subcommand
    sys.path.insert(0, ".")
    if invoked_subcommand != "init":
        if not os.path.exists(config):
            typer.secho("You must exec init first", )
            raise typer.Exit()
        parser.read(config)
        location = parser[name]["location"]
        tortoise_orm = parser[name]["tortoise_orm"]
        tortoise_config = get_tortoise_config(ctx, tortoise_orm)
        app = app or list(tortoise_config.get("apps").keys())[0]
        if "aerich.models" not in tortoise_config.get("apps").get(app).get("models"):
            typer.secho("Check your tortoise config and add aerich.models to it.")
            raise typer.Exit()
        ctx.obj["config"] = tortoise_config
        ctx.obj["location"] = location
        ctx.obj["app"] = app



@app.command()
@close_db
async def init_db(
    ctx: Context, safe: bool = typer.Option(
        True, help="When set to true, creates the table only when it does not already exist.", )
):
    """Generate schema and generate app migrate location."""
    config = ctx.obj["config"]
    location = ctx.obj["location"]
    app = ctx.obj["app"]
    dirname = os.path.join(location, app)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
        typer.secho(f"Success create app migrate location {dirname}", fg=typer.colors.GREEN)
    else:
        return typer.secho(f"Inited {app} already", fg=typer.colors.YELLOW)
    Migrate.write_old_models(config, app, location)
    await Tortoise.init(config=config)
    connection = get_app_connection(config, app)
    await generate_schema_for_client(connection, safe)
    schema = get_schema_sql(connection, safe)
    version = await Migrate.generate_version()
    await Aerich.create(version=version, app=app)
    with open(os.path.join(dirname, version), "w", encoding="utf-8") as f:
        content = {
            "upgrade": [schema],
        }
        json.dump(content, f, ensure_ascii=False, indent=2)
    return typer.secho(f'Success generate schema for app "{app}"', fg=typer.colors.GREEN)


@app.command()
@close_db
async def migrate(ctx: Context, name: str = typer.Option("update", help="Migrate name.")):
    """Generate migrate changes file."""
    app, config, location = await connect_tortoise(ctx)
    ret = await Migrate.migrate(name)
    if not ret:
        return typer.secho("No changes detected", fg=typer.colors.YELLOW)
    Migrate.write_old_models(config, app, location)
    typer.secho(f"Success migrate {ret}", fg=typer.colors.GREEN)


@app.command()
@close_db
async def upgrade(ctx: Context):
    """Upgrade to latest version."""
    app, config, location = await connect_tortoise(ctx)
    migrated = False
    for version in Migrate.get_all_version_files():
        try:
            exists = await Aerich.exists(version=version, app=app)
        except OperationalError:
            exists = False
        if not exists:
            async with in_transaction(get_app_connection_name(config, app)) as conn:
                file_path = os.path.join(Migrate.migrate_location, version)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    upgrade_query_list = content.get("upgrade")
                    for upgrade_query in upgrade_query_list:
                        await conn.execute_script(upgrade_query)
                await Aerich.create(version=version, app=app)
            typer.secho(f"Success upgrade {version}", fg=typer.colors.GREEN)
            migrated = True
    if not migrated:
        typer.secho("No migrate items", fg=typer.colors.YELLOW)


@app.command()
@close_db
async def downgrade(ctx: Context):
    """Downgrade to previous version."""
    app, config, location = await connect_tortoise(ctx)
    last_version = await Migrate.get_last_version()
    if not last_version:
        return typer.secho("No last version found", fg=typer.colors.YELLOW)
    file = last_version.version
    async with in_transaction(get_app_connection_name(config, app)) as conn:
        file_path = os.path.join(Migrate.migrate_location, file)
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            downgrade_query_list = content.get("downgrade")
            if not downgrade_query_list:
                return typer.secho("No downgrade item found", fg=typer.colors.YELLOW)
            for downgrade_query in downgrade_query_list:
                await conn.execute_query(downgrade_query)
            await last_version.delete()
        return typer.secho(f"Success downgrade {file}", fg=typer.colors.GREEN)


@app.command()
@close_db
async def heads(ctx: Context):
    """Show current available heads in migrate location."""
    app,config,location=await connect_tortoise(ctx)
    versions = Migrate.get_all_version_files()
    is_heads = False
    for version in versions:
        if not await Aerich.exists(version=version, app=app):
            typer.secho(version, fg=typer.colors.GREEN)
            is_heads = True
    if not is_heads:
        typer.secho("No available heads,try migrate", fg=typer.colors.GREEN)


@app.command()
@close_db
async def history(ctx: Context):
    """List all migrate items."""
    versions = Migrate.get_all_version_files()
    for version in versions:
        typer.secho(version, fg=typer.colors.GREEN)
    if not versions:
        typer.secho("No history,try migrate", fg=typer.colors.GREEN)


if __name__ == '__main__':
    app()
