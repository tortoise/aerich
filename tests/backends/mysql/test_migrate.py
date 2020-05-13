from tests.backends.mysql import DBTestCase


class TestMigrate(DBTestCase):
    async def test_migrate(self):
        self.migrate.diff_models_module('tests.models', 'tests.new_models')
        print(self.migrate.operators)
