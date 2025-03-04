# mypy: disable-error-code="no-redef"
from __future__ import annotations

import sys
from types import ModuleType

import tortoise

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import tomlkit as tomllib


def imports_tomlkit() -> ModuleType:
    try:
        import tomli_w as tomlkit
    except ImportError:
        import tomlkit
    return tomlkit


def tortoise_version_less_than(version: str) -> bool:
    # The min version of tortoise is '0.11.0', so we can compare it by a `<`,
    return tortoise.__version__ < version
