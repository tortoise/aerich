import importlib

from asyncclick import BadOptionUsage, Context
from tortoise import BaseDBAsyncClient, Tortoise


def get_app_connection_name(config, app) -> str:
    """
    get connection name
    :param config:
    :param app:
    :return:
    """
    return config.get("apps").get(app).get("default_connection")


def get_app_connection(config, app) -> BaseDBAsyncClient:
    """
    get connection name
    :param config:
    :param app:
    :return:
    """
    return Tortoise.get_connection(get_app_connection_name(config, app))


def get_tortoise_config(ctx: Context, tortoise_orm: str) -> dict:
    """
    get tortoise config from module
    :param ctx:
    :param tortoise_orm:
    :return:
    """
    splits = tortoise_orm.split(".")
    config_path = ".".join(splits[:-1])
    tortoise_config = splits[-1]
    try:
        config_module = importlib.import_module(config_path)
    except (ModuleNotFoundError, AttributeError):
        raise BadOptionUsage(
            ctx=ctx, message=f'No config named "{config_path}"', option_name="--config"
        )

    config = getattr(config_module, tortoise_config, None)
    if not config:
        raise BadOptionUsage(
            option_name="--config",
            message=f'Can\'t get "{tortoise_config}" from module "{config_module}"',
            ctx=ctx,
        )
    return config
