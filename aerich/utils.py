import importlib
from typing import Dict

from click import BadOptionUsage, Context
from tortoise import BaseDBAsyncClient, Tortoise


def get_app_connection_name(config, app) -> str:
    """
    get connection name
    :param config:
    :param app:
    :return:
    """
    return config.get("apps").get(app).get("default_connection", "default")


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


_UPGRADE = "##### upgrade #####\n"
_DOWNGRADE = "##### downgrade #####\n"


def get_version_content_from_file(version_file: str) -> Dict:
    """
    get version content
    :param version_file:
    :return:
    """
    with open(version_file, "r", encoding="utf-8") as f:
        content = f.read()
        first = content.index(_UPGRADE)
        second = content.index(_DOWNGRADE)
        upgrade_content = content[first + len(_UPGRADE) : second].strip()  # noqa:E203
        downgrade_content = content[second + len(_DOWNGRADE) :].strip()  # noqa:E203
        ret = {"upgrade": upgrade_content.split("\n"), "downgrade": downgrade_content.split("\n")}
        return ret


def write_version_file(version_file: str, content: Dict):
    """
    write version file
    :param version_file:
    :param content:
    :return:
    """
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(_UPGRADE)
        upgrade = content.get("upgrade")
        if len(upgrade) > 1:
            f.write(";\n".join(upgrade) + ";\n")
        else:
            f.write(f"{upgrade[0]};\n")
        downgrade = content.get("downgrade")
        if downgrade:
            f.write(_DOWNGRADE)
            if len(downgrade) > 1:
                f.write(";\n".join(downgrade) + ";\n")
            else:
                f.write(f"{downgrade[0]};\n")
