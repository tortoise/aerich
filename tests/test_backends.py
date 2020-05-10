from asynctest import TestCase
from tortoise import Tortoise

from alice.backends.mysql import MysqlDDL
from tests import User

TORTOISE_ORM = {
    'connections': {
        'default': 'mysql://root:123456@127.0.0.1:3306/fastapi-admin'
    },
    'apps': {
        'models': {
            'models': ['tests'],
            'default_connection': 'default',
        }
    }
}


class TestMysql(TestCase):
    async def setUp(self) -> None:
        await Tortoise.init(config=TORTOISE_ORM)

    async def test_create_table(self):
        ddl = MysqlDDL(Tortoise.get_connection('default'), User)
        print(ddl.create_table())

    async def tearDown(self) -> None:
        await Tortoise.close_connections()
