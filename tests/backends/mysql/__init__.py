from asynctest import TestCase
from tortoise import Tortoise

from alice.backends.mysql import MysqlDDL
from alice.migrate import Migrate

TORTOISE_ORM = {
    'connections': {
        'default': 'mysql://root:123456@127.0.0.1:3306/test',
    },
    'apps': {
        'models': {
            'models': ['tests.models'],
            'default_connection': 'default',
        },
    }
}


class DBTestCase(TestCase):
    async def setUp(self) -> None:
        await Tortoise.init(config=TORTOISE_ORM)
        self.client = Tortoise.get_connection('default')
        self.ddl = MysqlDDL(self.client)
        self.migrate = Migrate(ddl=self.ddl)

    async def tearDown(self) -> None:
        await Tortoise.close_connections()
