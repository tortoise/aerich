from tortoise import Tortoise

from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from aerich.migrate import Migrate


def test_migrate():
    apps = Tortoise.apps
    models = apps.get("models")
    diff_models = apps.get("diff_models")
    Migrate.diff_models(diff_models, models)
    Migrate.diff_models(models, diff_models, False)
    if isinstance(Migrate.ddl, MysqlDDL):
        assert Migrate.upgrade_operators == [
            "ALTER TABLE category ADD `name` VARCHAR(200) NOT NULL",
            "ALTER TABLE user ADD UNIQUE INDEX uid_user_usernam_9987ab (`username`)",
        ]
        assert Migrate.downgrade_operators == [
            "ALTER TABLE category DROP COLUMN name",
            "ALTER TABLE user DROP INDEX uid_user_usernam_9987ab",
        ]
    elif isinstance(Migrate.ddl, SqliteDDL):
        assert Migrate.upgrade_operators == [
            'ALTER TABLE category ADD "name" VARCHAR(200) NOT NULL',
            'ALTER TABLE user ADD UNIQUE INDEX uid_user_usernam_9987ab ("username")',
        ]
        assert Migrate.downgrade_operators == [
            "ALTER TABLE category DROP COLUMN name",
            "ALTER TABLE user DROP INDEX uid_user_usernam_9987ab",
        ]
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert Migrate.upgrade_operators == [
            'ALTER TABLE category ADD "name" VARCHAR(200) NOT NULL',
            'ALTER TABLE user ADD UNIQUE INDEX uid_user_usernam_9987ab ("username")',
        ]
        assert Migrate.downgrade_operators == [
            "ALTER TABLE category DROP COLUMN name",
            "ALTER TABLE user DROP INDEX uid_user_usernam_9987ab",
        ]
