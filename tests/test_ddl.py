from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from aerich.migrate import Migrate
from tests.models import Category


def test_create_table():
    ret = Migrate.ddl.create_table(Category)
    if isinstance(Migrate.ddl, MysqlDDL):
        assert (
            ret
            == """CREATE TABLE IF NOT EXISTS `category` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `slug` VARCHAR(200) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL COMMENT 'User',
    CONSTRAINT `fk_category_user_e2e3874c` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""
        )

    elif isinstance(Migrate.ddl, SqliteDDL):
        assert (
            ret
            == """CREATE TABLE IF NOT EXISTS "category" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "slug" VARCHAR(200) NOT NULL,
    "name" VARCHAR(200) NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE /* User */
);"""
        )

    elif isinstance(Migrate.ddl, PostgresDDL):
        assert (
            ret
            == """CREATE TABLE IF NOT EXISTS "category" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "slug" VARCHAR(200) NOT NULL,
    "name" VARCHAR(200) NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "category"."user_id" IS 'User';"""
        )


def test_drop_table():
    ret = Migrate.ddl.drop_table(Category)
    assert ret == "DROP TABLE IF EXISTS category"


def test_add_column():
    ret = Migrate.ddl.add_column(Category, Category._meta.fields_map.get("name"))
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret == "ALTER TABLE category ADD `name` VARCHAR(200) NOT NULL"
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'ALTER TABLE category ADD "name" VARCHAR(200) NOT NULL'
    elif isinstance(Migrate.ddl, SqliteDDL):
        assert ret == 'ALTER TABLE category ADD "name" VARCHAR(200) NOT NULL'


def test_drop_column():
    ret = Migrate.ddl.drop_column(Category, "name")
    assert ret == "ALTER TABLE category DROP COLUMN name"
    assert ret == "ALTER TABLE category DROP COLUMN name"


def test_add_index():
    index = Migrate.ddl.add_index(Category, ["name"])
    index_u = Migrate.ddl.add_index(Category, ["name"], True)
    if isinstance(Migrate.ddl, MysqlDDL):
        assert index == "ALTER TABLE category ADD  INDEX idx_category_name_8b0cb9 (`name`)"

        assert index_u == "ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 (`name`)"

    elif isinstance(Migrate.ddl, SqliteDDL):
        assert index_u == 'ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 ("name")'

        assert index_u == 'ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 ("name")'


def test_drop_index():
    ret = Migrate.ddl.drop_index(Category, ["name"])
    assert ret == "ALTER TABLE category DROP INDEX idx_category_name_8b0cb9"
    ret = Migrate.ddl.drop_index(Category, ["name"], True)
    assert ret == "ALTER TABLE category DROP INDEX uid_category_name_8b0cb9"


def test_add_fk():
    ret = Migrate.ddl.add_fk(Category, Category._meta.fields_map.get("user"))
    assert (
        ret
        == "ALTER TABLE category ADD CONSTRAINT `fk_category_user_e2e3874c` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE"
    )


def test_drop_fk():
    ret = Migrate.ddl.drop_fk(Category, Category._meta.fields_map.get("user"))
    assert ret == "ALTER TABLE category DROP FOREIGN KEY fk_category_user_e2e3874c"
