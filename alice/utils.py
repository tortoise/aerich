from tortoise import Tortoise


def get_app_connection(config: dict, app: str):
    """
    get tortoise connection by app
    :param config:
    :param app:
    :return:
    """
    return Tortoise.get_connection(config.get('apps').get(app).get('default_connection')),
