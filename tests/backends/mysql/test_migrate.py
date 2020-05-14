from asynctest import TestCase
from tortoise import Tortoise

from alice.migrate import Migrate
from tests.backends.mysql import TORTOISE_ORM


class TestMigrate(TestCase):
    async def setUp(self) -> None:
        await Migrate.init_with_old_models(TORTOISE_ORM, "models", "./migrations")

    async def test_migrate(self):
        Migrate.diff_model(
            Tortoise.apps.get("models").get("Category"),
            Tortoise.apps.get("diff_models").get("Category"),
        )
        print(Migrate.upgrade_operators)
