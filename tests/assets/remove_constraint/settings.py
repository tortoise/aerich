import os
from datetime import date

from tortoise.contrib.test import MEMORY_SQLITE

DB_URL = (
    _u.replace("\\{\\}", f"aerich_remove_constraint_{date.today():%Y%m%d}")
    if (_u := os.getenv("TEST_DB"))
    else MEMORY_SQLITE
)
DB_URL_SECOND = (DB_URL + "_second") if DB_URL != MEMORY_SQLITE else MEMORY_SQLITE

TORTOISE_ORM = {
    "connections": {
        "default": DB_URL.replace(MEMORY_SQLITE, "sqlite://db.sqlite3"),
    },
    "apps": {
        "models": {"models": ["models", "aerich.models"], "default_connection": "default"},
    },
}
