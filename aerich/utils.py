import importlib
import os
import re
import sys
from pathlib import Path
from typing import Dict

from click import BadOptionUsage, ClickException, Context
from tortoise import BaseDBAsyncClient, Tortoise


def add_src_path(path: str) -> str:
    """
    add a folder to the paths so we can import from there
    :param path: path to add
    :return: absolute path
    """
    if not os.path.isabs(path):
        # use the absolute path, otherwise some other things (e.g. __file__) won't work properly
        path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise ClickException(f"Specified source folder does not exist: {path}")
    if path not in sys.path:
        sys.path.insert(0, path)
    return path


def get_app_connection_name(config, app_name: str) -> str:
    """
    get connection name
    :param config:
    :param app_name:
    :return:
    """
    app = config.get("apps").get(app_name)
    if app:
        return app.get("default_connection", "default")
    raise BadOptionUsage(
        option_name="--app", message=f'Can\'t get app named "{app_name}"',
    )


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
    except ModuleNotFoundError as e:
        raise ClickException(f"Error while importing configuration module: {e}") from None

    config = getattr(config_module, tortoise_config, None)
    if not config:
        raise BadOptionUsage(
            option_name="--config",
            message=f'Can\'t get "{tortoise_config}" from module "{config_module}"',
            ctx=ctx,
        )
    return config


_UPGRADE = "-- upgrade --\n"
_DOWNGRADE = "-- downgrade --\n"


def get_version_content_from_file(version_file: str) -> Dict:
    """
    get version content
    :param version_file:
    :return:
    """
    with open(version_file, "r", encoding="utf-8") as f:
        content = f.read()
        first = content.index(_UPGRADE)
        try:
            second = content.index(_DOWNGRADE)
        except ValueError:
            second = len(content) - 1
        upgrade_content = content[first + len(_UPGRADE) : second].strip()  # noqa:E203
        downgrade_content = content[second + len(_DOWNGRADE) :].strip()  # noqa:E203
        ret = {
            "upgrade": list(filter(lambda x: x or False, upgrade_content.split(";\n"))),
            "downgrade": list(filter(lambda x: x or False, downgrade_content.split(";\n"))),
        }
        return ret


def write_version_file(version_file: Path, content: Dict):
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
            f.write(f"{upgrade[0]}")
            if not upgrade[0].endswith(";"):
                f.write(";")
            f.write("\n")
        downgrade = content.get("downgrade")
        if downgrade:
            f.write(_DOWNGRADE)
            if len(downgrade) > 1:
                f.write(";\n".join(downgrade) + ";\n")
            else:
                f.write(f"{downgrade[0]};\n")


def get_models_describe(app: str) -> Dict:
    """
    get app models describe
    :param app:
    :return:
    """
    ret = {}
    for model in Tortoise.apps.get(app).values():
        describe = model.describe()
        ret[describe.get("name")] = describe
    return ret


def is_default_function(string: str):
    return re.match(r"^<function.+>$", str(string or ""))
