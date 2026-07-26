import os
from datetime import date

from tortoise.contrib.test import MEMORY_SQLITE

DB_URL = MEMORY_SQLITE
if _u := os.getenv("TEST_DB"):
    _db_name = f"aerich_remove_constraint_{date.today():%Y%m%d}"
    _u = _u.replace("\\{\\}", _db_name)  # For Linux
    DB_URL = _u.replace("/{/}", _db_name)  # For Windows
DB_URL_SECOND = (DB_URL + "_second") if DB_URL != MEMORY_SQLITE else MEMORY_SQLITE

TORTOISE_ORM = {
    "connections": {
        "default": DB_URL.replace(MEMORY_SQLITE, "sqlite://db.sqlite3"),
    },
    "apps": {
        "models": {"models": ["models", "aerich.models"], "default_connection": "default"},
    },
}
