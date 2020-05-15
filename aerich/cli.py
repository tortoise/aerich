import importlib
import json
import os
import sys
from enum import Enum

import asyncclick as click
from asyncclick import BadOptionUsage, Context, UsageError
from tortoise import Tortoise, generate_schema_for_client

from aerich.migrate import Migrate
from aerich.utils import get_app_connection


class Color(str, Enum):
    green = "green"
    red = "red"
    yellow = "yellow"


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    default="settings",
    show_default=True,
    help="Tortoise-ORM config module, will auto read dict config variable from it.",
)
@click.option(
    "--tortoise-orm",
    default="TORTOISE_ORM",
    show_default=True,
    help="Tortoise-ORM config dict variable.",
)
@click.option(
    "--location", default="./migrations", show_default=True, help="Migrate store location."
)
@click.option("--app", default="models", show_default=True, help="Tortoise-ORM app name.")
@click.pass_context
async def cli(ctx: Context, config, tortoise_orm, location, app):
    ctx.ensure_object(dict)
    try:
        config_module = importlib.import_module(config, ".")
    except ModuleNotFoundError:
        raise BadOptionUsage(ctx=ctx, message=f'No module named "{config}"', option_name="--config")
    config = getattr(config_module, tortoise_orm, None)
    if not config:
        raise BadOptionUsage(
            option_name="--config",
            message=f'Can\'t get "{tortoise_orm}" from module "{config_module}"',
            ctx=ctx,
        )

    if app not in config.get("apps").keys():
        raise BadOptionUsage(option_name="--config", message=f'No app found in "{config}"', ctx=ctx)

    ctx.obj["config"] = config
    ctx.obj["location"] = location
    ctx.obj["app"] = app

    if ctx.invoked_subcommand == "init":
        await Tortoise.init(config=config)
    else:
        if not os.path.isdir(location):
            raise UsageError("You must exec init first", ctx=ctx)
        await Migrate.init_with_old_models(config, app, location)


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
    connection = get_app_connection(config, app)
    available_versions = Migrate.get_all_version_files(is_all=False)
    if not available_versions:
        return click.secho("No migrate items", fg=Color.yellow)
    async with connection._in_transaction() as conn:
        for file in available_versions:
            file_path = os.path.join(Migrate.migrate_location, file)
            with open(file_path, "r") as f:
                content = json.load(f)
                upgrade_query_list = content.get("upgrade")
                for upgrade_query in upgrade_query_list:
                    await conn.execute_query(upgrade_query)

            with open(file_path, "w") as f:
                content["migrate"] = True
                json.dump(content, f, indent=4)
                click.secho(f"Success upgrade {file}", fg=Color.green)


@cli.command(help="Downgrade to previous version.")
@click.pass_context
async def downgrade(ctx: Context):
    app = ctx.obj["app"]
    config = ctx.obj["config"]
    connection = get_app_connection(config, app)
    available_versions = Migrate.get_all_version_files()
    if not available_versions:
        return click.secho("No migrate items", fg=Color.yellow)

    async with connection._in_transaction() as conn:
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
                json.dump(content, f, indent=4)
                return click.secho(f"Success downgrade {file}", fg=Color.green)


@cli.command(help="Show current available heads in migrate location.")
@click.pass_context
def heads(ctx: Context):
    for version in Migrate.get_all_version_files(is_all=False):
        click.secho(version, fg=Color.yellow)


@cli.command(help="List all migrate items.")
@click.pass_context
def history(ctx):
    for version in Migrate.get_all_version_files():
        click.secho(version, fg=Color.yellow)


@cli.command(help="Init migrate location and generate schema, you must exec first.")
@click.option(
    "--safe",
    is_flag=True,
    default=True,
    help="When set to true, creates the table only when it does not already exist.",
    show_default=True,
)
@click.pass_context
async def init(ctx: Context, safe):
    location = ctx.obj["location"]
    app = ctx.obj["app"]
    config = ctx.obj["config"]

    if not os.path.isdir(location):
        os.mkdir(location)

    dirname = os.path.join(location, app)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
        click.secho(f"Success create migrate location {dirname}", fg=Color.green)
    else:
        return click.secho(f'Already inited app "{app}"', fg=Color.yellow)

    Migrate.write_old_models(config, app, location)

    connection = get_app_connection(config, app)
    await generate_schema_for_client(connection, safe)

    return click.secho(f'Success init for app "{app}"', fg=Color.green)


def main():
    sys.path.insert(0, ".")
    cli(_anyio_backend="asyncio")
