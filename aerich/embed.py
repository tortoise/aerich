from tortoise import Tortoise

from aerich.actions import init_db_action
from aerich.output import PrintOutput, Output


class Aerich:
    def __init__(
        self,
        app_name: str = "models",
        location: str = "migrations",
        connection_name: str = "default",
        output: Output = None,
    ):
        self.__app_name = app_name
        self.__location = location
        self.__connection_name = connection_name
        self.__output = output or PrintOutput()

    async def init_db(self, safe: bool = True) -> bool:
        connection = Tortoise.get_connection(connection_name=self.__connection_name)
        await init_db_action(
            app_name=self.__app_name,
            location=self.__location,
            connection=connection,
            output=self.__output,
            safe=safe,
        )
