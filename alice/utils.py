from tortoise import Tortoise


def get_app_connection(config, app):
    """
    get tortoise app
    :param config:
    :param app:
    :return:
    """
    return Tortoise.get_connection(config.get("apps").get(app).get("default_connection"))
