from tortoise import Tortoise
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.contrib import test

from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from tests.models import Category


class TestDDL(test.TruncationTestCase):
    maxDiff = None

    def setUp(self) -> None:
        client = Tortoise.get_connection("models")
        if client.schema_generator is MySQLSchemaGenerator:
            self.ddl = MysqlDDL(client)
        elif client.schema_generator is SqliteSchemaGenerator:
            self.ddl = SqliteDDL(client)
        elif client.schema_generator is AsyncpgSchemaGenerator:
            self.ddl = PostgresDDL(client)

    def test_create_table(self):
        ret = self.ddl.create_table(Category)
        if isinstance(self.ddl, MysqlDDL):
            self.assertEqual(
                ret,
                """CREATE TABLE IF NOT EXISTS `category` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `slug` VARCHAR(200) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL COMMENT 'User',
    CONSTRAINT `fk_category_user_e2e3874c` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;""",
            )
        elif isinstance(self.ddl, SqliteDDL):
            self.assertEqual(
                ret,
                """CREATE TABLE IF NOT EXISTS "category" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "slug" VARCHAR(200) NOT NULL,
    "name" VARCHAR(200) NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE /* User */
);""",
            )
        elif isinstance(self.ddl, PostgresDDL):
            print(ret)
            self.assertEqual(
                ret,
                """CREATE TABLE IF NOT EXISTS "category" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "slug" VARCHAR(200) NOT NULL,
    "name" VARCHAR(200) NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "category"."user_id" IS 'User';""",
            )

    def test_drop_table(self):
        ret = self.ddl.drop_table(Category)
        self.assertEqual(ret, "DROP TABLE IF EXISTS category")

    def test_add_column(self):
        ret = self.ddl.add_column(Category, Category._meta.fields_map.get("name"))
        if isinstance(self.ddl, MysqlDDL):
            self.assertEqual(ret, "ALTER TABLE category ADD `name` VARCHAR(200) NOT NULL")
        elif isinstance(self.ddl, PostgresDDL):
            self.assertEqual(ret, 'ALTER TABLE category ADD "name" VARCHAR(200) NOT NULL')
        elif isinstance(self.ddl, SqliteDDL):
            self.assertEqual(ret, 'ALTER TABLE category ADD "name" VARCHAR(200) NOT NULL')

    def test_drop_column(self):
        ret = self.ddl.drop_column(Category, "name")
        self.assertEqual(ret, "ALTER TABLE category DROP COLUMN name")
        self.assertEqual(ret, "ALTER TABLE category DROP COLUMN name")

    def test_add_index(self):
        index = self.ddl.add_index(Category, ["name"])
        index_u = self.ddl.add_index(Category, ["name"], True)
        if isinstance(self.ddl, MysqlDDL):
            self.assertEqual(
                index, "ALTER TABLE category ADD  INDEX idx_category_name_8b0cb9 (`name`)"
            )
            self.assertEqual(
                index_u, "ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 (`name`)"
            )
        elif isinstance(self.ddl, SqliteDDL):
            self.assertEqual(
                index_u, 'ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 ("name")'
            )
            self.assertEqual(
                index_u, 'ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 ("name")'
            )

    def test_drop_index(self):
        ret = self.ddl.drop_index(Category, ["name"])
        self.assertEqual(ret, "ALTER TABLE category DROP INDEX idx_category_name_8b0cb9")
        ret = self.ddl.drop_index(Category, ["name"], True)
        self.assertEqual(ret, "ALTER TABLE category DROP INDEX uid_category_name_8b0cb9")

    def test_add_fk(self):
        ret = self.ddl.add_fk(Category, Category._meta.fields_map.get("user"))
        self.assertEqual(
            ret,
            "ALTER TABLE category ADD CONSTRAINT `fk_category_user_e2e3874c` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE",
        )

    def test_drop_fk(self):
        ret = self.ddl.drop_fk(Category, Category._meta.fields_map.get("user"))
        self.assertEqual(ret, "ALTER TABLE category DROP FOREIGN KEY fk_category_user_e2e3874c")
