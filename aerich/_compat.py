# mypy: disable-error-code="no-redef"
from __future__ import annotations

import sys
from types import ModuleType

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import tomlkit as tomllib


def get_tomlkit() -> ModuleType:
    try:
        import tomli_w as tomlkit
    except ImportError:
        import tomlkit
    return tomlkit
