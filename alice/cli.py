import importlib
import json
import os
import sys
from enum import Enum

import asyncclick as click
from asyncclick import BadParameter, ClickException
from tortoise import generate_schema_for_client, ConfigurationError, Tortoise

from alice.migrate import Migrate
from alice.utils import get_app_connection

sys.path.append(os.getcwd())


class Color(str, Enum):
    green = "green"
    red = "red"


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    default="settings",
    show_default=True,
    help="Tortoise-ORM config module, will read config variable from it.",
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
async def cli(ctx, config, tortoise_orm, location, app):
    ctx.ensure_object(dict)
    try:
        config_module = importlib.import_module(config)
    except ModuleNotFoundError:
        raise BadParameter(param_hint=["--tortoise-orm"], message=f'No module named "{config}"')
    config = getattr(config_module, tortoise_orm, None)
    if not config:
        raise BadParameter(
            param_hint=["--config"],
            message=f'Can\'t get "{tortoise_orm}" from module "{config_module}"',
        )
    if app not in config.get("apps").keys():
        raise BadParameter(param_hint=["--app"], message=f'No app found in "{config}"')

    ctx.obj["config"] = config
    ctx.obj["location"] = location
    ctx.obj["app"] = app
    try:
        await Migrate.init_with_old_models(config, app, location)
    except ConfigurationError:
        pass


@cli.command(help="Generate migrate changes file.")
@click.option("--name", default="update", show_default=True, help="Migrate name.")
@click.pass_context
async def migrate(ctx, name):
    config = ctx.obj["config"]
    location = ctx.obj["location"]
    app = ctx.obj["app"]

    ret = Migrate.migrate(name)
    if not ret:
        click.secho("No changes detected", fg=Color.green)
    else:
        Migrate.write_old_models(config, app, location)
        click.secho(f"Success migrate {ret}", fg=Color.green)


@cli.command(help="Upgrade to latest version.")
@click.pass_context
async def upgrade(ctx):
    app = ctx.obj["app"]
    config = ctx.obj["config"]
    connection = get_app_connection(config, app)
    available_versions = Migrate.get_all_version_files(is_all=False)
    if not available_versions:
        return click.secho("No migrate items", fg=Color.green)
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
async def downgrade(ctx):
    app = ctx.obj["app"]
    config = ctx.obj["config"]
    connection = get_app_connection(config, app)
    available_versions = Migrate.get_all_version_files()
    if not available_versions:
        return click.secho("No migrate items", fg=Color.green)

    async with connection._in_transaction() as conn:
        for file in available_versions:
            file_path = os.path.join(Migrate.migrate_location, file)
            with open(file_path, "r") as f:
                content = json.load(f)
                if content.get("migrate"):
                    downgrade_query_list = content.get("downgrade")
                    for downgrade_query in downgrade_query_list:
                        await conn.execute_query(downgrade_query)

            with open(file_path, "w") as f:
                content["migrate"] = False
                json.dump(content, f, indent=4)
                return click.secho(f"Success downgrade {file}", fg=Color.green)


@cli.command(help="Show current available heads in migrate location.")
@click.pass_context
def heads(ctx):
    for version in Migrate.get_all_version_files(is_all=False):
        click.secho(version, fg=Color.green)


@cli.command(help="List all migrate items.")
@click.pass_context
def history(ctx):
    for version in Migrate.get_all_version_files():
        click.secho(version, fg=Color.green)


@cli.command(
    help="Init migrate location and generate schema, you must call first before other actions."
)
@click.option(
    "--safe",
    is_flag=True,
    default=True,
    help="When set to true, creates the table only when it does not already exist.",
    show_default=True,
)
@click.pass_context
async def init(ctx, safe):
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
        raise ClickException(f"Already inited app `{app}`")

    Migrate.write_old_models(config, app, location)

    await Migrate.init_with_old_models(config, app, location)
    await generate_schema_for_client(get_app_connection(config, app), safe)

    click.secho(f"Success init for app `{app}`", fg=Color.green)


def main():
    cli(_anyio_backend="asyncio")
