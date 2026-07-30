# mypy: disable-error-code="no-redef"
from __future__ import annotations

import platform
import sys
from types import ModuleType

import tortoise
from tortoise import Tortoise

if sys.version_info >= (3, 11):
    import tomllib
    from typing import Self
else:
    from typing_extensions import Self

    try:
        import tomli as tomllib
    except ImportError:
        import tomlkit as tomllib


__all__ = ("Self", "imports_tomlkit", "tomllib", "tortoise_version_less_than")


def imports_tomlkit() -> ModuleType:
    try:
        import tomli_w as tomlkit
    except ImportError:
        import tomlkit
    return tomlkit


def tortoise_version_less_than(version: str) -> bool:
    # The min version of tortoise is '0.11.0', so we can compare it by a `<`,
    return tortoise.__version__ < version


def is_tortoise_inited() -> bool:
    if (is_inited := getattr(Tortoise, "is_inited", None)) is not None:  # For tortoise>=1.0
        return is_inited()
    return Tortoise._inited


def _init_asyncio_patch() -> None:
    """
    Select compatible event loop for psycopg3.

    As of Python 3.8+, the default event loop on Windows is `proactor`,
    however psycopg3 requires the old default "selector" event loop.
    See https://www.psycopg.org/psycopg3/docs/advanced/async.html
    """
    if platform.system() == "Windows":
        try:
            from asyncio import WindowsSelectorEventLoopPolicy  # type:ignore
        except ImportError:
            pass  # Can't assign a policy which doesn't exist.
        else:
            from asyncio import get_event_loop_policy, set_event_loop_policy

            if not isinstance(get_event_loop_policy(), WindowsSelectorEventLoopPolicy):
                set_event_loop_policy(WindowsSelectorEventLoopPolicy())
