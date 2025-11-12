import os
from datetime import date

from tortoise.contrib.test import MEMORY_SQLITE

DB_URL = MEMORY_SQLITE
if _u := os.getenv("TEST_DB"):
    _db_name = f"aerich_missing_models_{date.today():%Y%m%d}"
    _u = _u.replace("\\{\\}", _db_name)  # For Linux
    DB_URL = _u.replace("/{/}", _db_name)  # For Windows

TORTOISE_ORM = {
    "connections": {
        "default": DB_URL.replace(MEMORY_SQLITE, "sqlite://db.sqlite3"),
    },
    "apps": {"models": {"models": ["models", "aerich.models"]}},
}
TORTOISE_ORM_NO_AERICH_MODELS = {
    **TORTOISE_ORM,
    "apps": {
        "models": {"models": ["models"]},
    },
}
TORTOISE_ORM_MULTI_APPS_WITHOUT_AERICH_MODELS = {
    **TORTOISE_ORM,
    "apps": {
        "models": {"models": ["models"]},
        "other_models": {"models": ["other_models"]},
    },
}
TORTOISE_ORM_MULTI_APPS = {
    **TORTOISE_ORM,
    "apps": {
        "models": {"models": ["models", "aerich.models"]},
        "other_models": {"models": ["other_models"]},
    },
}
