TORTOISE_ORM = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "auth": {"models": ["auth.models", "aerich.models"]},
        "polls": {"models": ["polls.models"]},
    },
}
