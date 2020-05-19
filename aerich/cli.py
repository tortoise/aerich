import json
import os
import sys
from configparser import ConfigParser
from enum import Enum
from . import __version__
import asyncclick as click
from asyncclick import Context, UsageError
from tortoise import ConfigurationError, Tortoise, generate_schema_for_client
from tortoise.transactions import in_transaction

from aerich.migrate import Migrate
from aerich.utils import get_app_connection, get_app_connection_name, get_tortoise_config


class Color(str, Enum):
    green = "green"
    red = "red"
    yellow = "yellow"


parser = ConfigParser()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
@click.option(
    "-c", "--config", default="aerich.ini", show_default=True, help="Config file.",
)
@click.option("--app", default="models", show_default=True, help="Tortoise-ORM app name.")
@click.option(
    "-n",
    "--name",
    default="aerich",
    show_default=True,
    help="Name of section in .ini file to use for aerich config.",
)
@click.pass_context
async def cli(ctx: Context, config, app, name):
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["name"] = name
    invoked_subcommand = ctx.invoked_subcommand
    if invoked_subcommand != "init":
        if not os.path.exists(config):
            raise UsageError("You must exec init first", ctx=ctx)
        parser.read(config)

        location = parser[name]["location"]
        tortoise_orm = parser[name]["tortoise_orm"]

        tortoise_config = get_tortoise_config(ctx, tortoise_orm)

        ctx.obj["config"] = tortoise_config
        ctx.obj["location"] = location
        ctx.obj["app"] = app

        if invoked_subcommand != "init-db":
            try:
                await Migrate.init_with_old_models(tortoise_config, app, location)
            except ConfigurationError:
                raise UsageError(ctx=ctx, message="You must exec ini-db first")


@cli.command(help="Generate migrate changes file.")
@click.option("--name", default="update", show_default=True, help="Migrate name.")
@click.pass_context
async def migrate(ctx: Context, name):
    config = ctx.obj["config"]
    location = ctx.obj["location"]
    app = ctx.obj["app"]

    ret = Migrate.migrate(name)
    if not ret:
        return click.secho("No changes detected", fg=Color.yellow)
    Migrate.write_old_models(config, app, location)
    click.secho(f"Success migrate {ret}", fg=Color.green)


@cli.command(help="Upgrade to latest version.")
@click.pass_context
async def upgrade(ctx: Context):
    app = ctx.obj["app"]
    config = ctx.obj["config"]
    available_versions = Migrate.get_all_version_files(is_all=False)
    if not available_versions:
        return click.secho("No migrate items", fg=Color.yellow)
    async with in_transaction(get_app_connection_name(config, app)) as conn:
        for file in available_versions:
            file_path = os.path.join(Migrate.migrate_location, file)
            with open(file_path, "r") as f:
                content = json.load(f)
                upgrade_query_list = content.get("upgrade")
                for upgrade_query in upgrade_query_list:
                    await conn.execute_query(upgrade_query)

            with open(file_path, "w") as f:
                content["migrate"] = True
                json.dump(content, f, indent=2, ensure_ascii=False)
                click.secho(f"Success upgrade {file}", fg=Color.green)


@cli.command(help="Downgrade to previous version.")
@click.pass_context
async def downgrade(ctx: Context):
    app = ctx.obj["app"]
    config = ctx.obj["config"]
    available_versions = Migrate.get_all_version_files()
    if not available_versions:
        return click.secho("No migrate items", fg=Color.yellow)

    async with in_transaction(get_app_connection_name(config, app)) as conn:
        for file in reversed(available_versions):
            file_path = os.path.join(Migrate.migrate_location, file)
            with open(file_path, "r") as f:
                content = json.load(f)
                if content.get("migrate"):
                    downgrade_query_list = content.get("downgrade")
                    for downgrade_query in downgrade_query_list:
                        await conn.execute_query(downgrade_query)
                else:
                    continue
            with open(file_path, "w") as f:
                content["migrate"] = False
                json.dump(content, f, indent=2, ensure_ascii=False)
                return click.secho(f"Success downgrade {file}", fg=Color.green)


@cli.command(help="Show current available heads in migrate location.")
@click.pass_context
def heads(ctx: Context):
    for version in Migrate.get_all_version_files(is_all=False):
        click.secho(version, fg=Color.green)


@cli.command(help="List all migrate items.")
@click.pass_context
def history(ctx):
    for version in Migrate.get_all_version_files():
        click.secho(version, fg=Color.green)


@cli.command(help="Init config file and generate root migrate location.")
@click.option(
    "-t",
    "--tortoise-orm",
    required=True,
    help="Tortoise-ORM config module dict variable, like settings.TORTOISE_ORM.",
)
@click.option(
    "--location", default="./migrations", show_default=True, help="Migrate store location."
)
@click.pass_context
async def init(
        ctx: Context, tortoise_orm, location,
):
    config = ctx.obj["config"]
    name = ctx.obj["name"]

    parser.add_section(name)
    parser.set(name, "tortoise_orm", tortoise_orm)
    parser.set(name, "location", location)

    with open(config, "w") as f:
        parser.write(f)

    if not os.path.isdir(location):
        os.mkdir(location)

    click.secho(f"Success create migrate location {location}", fg=Color.green)
    click.secho(f"Success generate config file {config}", fg=Color.green)


@cli.command(help="Generate schema and generate app migrate location.")
@click.option(
    "--safe",
    is_flag=True,
    default=True,
    help="When set to true, creates the table only when it does not already exist.",
    show_default=True,
)
@click.pass_context
async def init_db(ctx: Context, safe):
    config = ctx.obj["config"]
    location = ctx.obj["location"]
    app = ctx.obj["app"]

    dirname = os.path.join(location, app)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
        click.secho(f"Success create app migrate location {dirname}", fg=Color.green)
    else:
        return click.secho(f'Already inited app "{app}"', fg=Color.yellow)

    Migrate.write_old_models(config, app, location)

    await Tortoise.init(config=config)
    connection = get_app_connection(config, app)
    await generate_schema_for_client(connection, safe)

    return click.secho(f'Success generate schema for app "{app}"', fg=Color.green)


def main():
    sys.path.insert(0, ".")
    cli(_anyio_backend="asyncio")
