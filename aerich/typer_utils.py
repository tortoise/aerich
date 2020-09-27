import importlib

import typer
from tortoise import BaseDBAsyncClient, Tortoise
from typer import Context


def get_app_connection_name(config, app) -> str:
    """
    get connection name
    """
    return config.get("apps").get(app).get("default_connection", "default")


def get_app_connection(config, app) -> BaseDBAsyncClient:
    """
    get connection name
    """
    return Tortoise.get_connection(get_app_connection_name(config, app))


def get_tortoise_config(ctx: Context, tortoise_orm: str) -> dict:
    """
    get tortoise config from module
    """
    splits = tortoise_orm.split(".")
    config_path = ".".join(splits[:-1])
    tortoise_config = splits[-1]
    try:
        config_module = importlib.import_module(config_path)
    except (ModuleNotFoundError, AttributeError):
        typer.echo(f'No config named "{config_path}"')
        raise typer.Exit()

    config = getattr(config_module, tortoise_config, None)
    if not config:
        typer.echo(f'Can\'t get "{tortoise_config}" from module "{config_module}"',)
        raise typer.Exit()
    return config


def ask_rename_column(old_name: str, new_name: str, model_name: str) -> bool:
    return typer.confirm(f"Do you want change  {old_name} to {new_name} in {model_name}?")
