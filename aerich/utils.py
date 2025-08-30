from __future__ import annotations

import importlib.util
import os
import pkgutil
import re
import sys
from collections.abc import Awaitable, Callable, Generator
from importlib.machinery import FileFinder
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar, cast

from anyio import from_thread
from asyncclick import BadOptionUsage, ClickException, Context
from dictdiffer import diff
from tortoise import BaseDBAsyncClient, Tortoise
from tortoise.log import logger

from aerich.exceptions import NotInitedError

if sys.version_info >= (3, 11):
    from typing import ParamSpec, TypeVarTuple, Unpack
else:
    from typing_extensions import ParamSpec, TypeVarTuple, Unpack

T_Retval = TypeVar("T_Retval")
PosArgsT = TypeVarTuple("PosArgsT")
P = ParamSpec("P")


def add_src_path(path: str) -> str:
    """
    add a folder to the paths, so we can import from there
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


def get_app_connection_name(config: dict[str, dict[str, Any]], app_name: str) -> str:
    """
    get connection name
    :param config:
    :param app_name:
    :return: the default connection name (Usally it is 'default')
    """
    if app := config["apps"].get(app_name):
        return cast(str, app.get("default_connection", "default"))
    raise BadOptionUsage(option_name="--app", message=f"Can't get app named {app_name!r}")


def get_app_connection(config: dict[str, Any], app: str) -> BaseDBAsyncClient:
    """
    get connection client
    :param config:
    :param app:
    :return: client instance
    """
    return Tortoise.get_connection(get_app_connection_name(config, app))


def get_tortoise_config(ctx: Context, tortoise_orm: str) -> dict[str, Any]:
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
        if len(splits) < 3:
            raise ClickException(f"Error while importing configuration module: {e}") from None
        module_path = ".".join(splits[:-2])
        try:
            config_module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise ClickException(f"Failed to import configuration module: {e}") from None
        tortoise_config = splits[-2] + "." + splits[-1]
        config_class = getattr(config_module, splits[-2], None)
        config = getattr(config_class, splits[-1], None)
    else:
        config = getattr(config_module, tortoise_config, None)
    if not config:
        raise BadOptionUsage(
            option_name="--config",
            message=f'Can\'t get "{tortoise_config}" from module "{config_module}"',
            ctx=ctx,
        )
    return cast(dict[str, Any], config)


def get_models_describe(app: str) -> dict[str, dict[str, Any]]:
    """
    get app models describe
    :param app:
    :return:
    """
    ret: dict[str, dict[str, Any]] = {}
    try:
        app_config = Tortoise.apps[app]
    except KeyError as e:
        if not Tortoise._inited:
            raise NotInitedError("Tortoise not inited yet.") from e
        logger.debug(f"{Tortoise.apps.keys() = }")
        raise e
    for model in app_config.values():
        managed = getattr(model.Meta, "managed", None)
        describe = model.describe()
        try:
            qualified_model_name = describe["name"]
        except KeyError:
            continue
        else:
            ret[qualified_model_name] = dict(describe, managed=managed)
    return ret


def is_default_function(string: Any) -> re.Match[str] | None:
    return re.match(r"^<function.+>$", str(string or ""))


def file_module_info(path: str | Path, name: str) -> pkgutil.ModuleInfo:
    for module_info in pkgutil.iter_modules([str(path)]):
        if module_info.name == name:
            return module_info
    raise FileNotFoundError(f"Module {name} not found in path {path}")


def import_py_file(file: str | Path) -> ModuleType:
    module_name, file_ext = os.path.splitext(os.path.split(file)[-1])
    spec = importlib.util.spec_from_file_location(module_name, file)
    module = importlib.util.module_from_spec(spec)  # type:ignore[arg-type]
    spec.loader.exec_module(module)  # type:ignore[union-attr]
    return module


def import_py_module(module_info: pkgutil.ModuleInfo) -> ModuleType:
    module_finder: FileFinder
    name: str
    ispkg: bool
    module_finder, name, ispkg = module_info  # type:ignore[assignment]
    module_finder.invalidate_caches()
    spec = module_finder.find_spec(name)
    module = importlib.util.module_from_spec(spec)  # type:ignore[arg-type]
    spec.loader.exec_module(module)  # type:ignore[union-attr]
    return module


def py_module_path(module_info: pkgutil.ModuleInfo) -> Path:
    module_finder: FileFinder
    name: str
    ispkg: bool
    module_finder, name, ispkg = module_info  # type:ignore[assignment]
    module_finder.invalidate_caches()
    spec = module_finder.find_spec(name)
    if not spec or not spec.origin or not Path(spec.origin).is_file():
        raise FileNotFoundError(f"Module {name} not found in {module_finder.path}.")
    return Path(spec.origin)


def get_dict_diff_by_key(
    old_fields: list[dict],
    new_fields: list[dict],
    key: str = "through",
    second_key: str = "forward_key",
) -> Generator[tuple[str, Any, Any]]:
    """
    Compare two list by key instead of by index

    :param old_fields: previous field info list
    :param new_fields: current field info list
    :param key: if two dicts have the same value of this key, action is change; otherwise, is remove/add
    :param second_key: if multi fields with same value of key, use `(field[key], field[second_key])` as ident
    :return: similar to dictdiffer.diff

    Example::

        >>> old = [{'through': 'a'}, {'through': 'b'}, {'through': 'c'}]
        >>> new = [{'through': 'a'}, {'through': 'c'}]  # remove the second element
        >>> list(diff(old, new))
        [('change', [1, 'through'], ('b', 'c')),
         ('remove', '', [(2, {'through': 'c'})])]
        >>> list(get_dict_diff_by_key(old, new))
        [('remove', '', [(0, {'through': 'b'})])]

    """
    length_old, length_new = len(old_fields), len(new_fields)
    if length_old == 0 or length_new == 0 or length_old == length_new == 1:
        yield from diff(old_fields, new_fields)
    else:
        should_use_second_key = len({i[key] for i in old_fields}) < length_old or (
            len({i[key] for i in new_fields}) < length_new
        )
        value_index: dict[str | tuple[str, str], int] = (
            {(f[key], f[second_key]): i for i, f in enumerate(new_fields)}
            if should_use_second_key
            else {f[key]: i for i, f in enumerate(new_fields)}
        )
        additions = set(range(length_new))
        for field in old_fields:
            value = (field[key], field[second_key]) if should_use_second_key else field[key]
            if (index := value_index.get(value)) is not None:
                additions.remove(index)
                yield from diff([field], [new_fields[index]])  # change
            else:
                yield from diff([field], [])  # remove
        if additions:
            for index in sorted(additions):
                yield from diff([], [new_fields[index]])  # add


def run_async(
    async_func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
    *args: Unpack[PosArgsT],
) -> T_Retval:
    """Run async function in worker thread and get the result of it"""
    # `asyncio.run(async_func())` can get the result of async function,
    # but it will close the running loop.
    result: list[T_Retval] = []

    async def runner() -> None:
        res = await async_func(*args)
        result.append(res)

    with from_thread.start_blocking_portal() as portal:
        portal.call(runner)

    return result[0]
