TORTOISE_ORM = {
    "connections": {"default": "mysql://root:123456@127.0.0.1:3306/test"},
    "apps": {
        "models": {"models": ["tests.models", "aerich.models"], "default_connection": "default",},
    },
}
