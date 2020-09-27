import pytest

from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from aerich.exceptions import NotSupportError
from aerich.migrate import Migrate
from tests.models import Category, User


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
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret == "DROP TABLE IF EXISTS `category`"
    else:
        assert ret == 'DROP TABLE IF EXISTS "category"'


def test_add_column():
    ret = Migrate.ddl.add_column(Category, Category._meta.fields_map.get("name"))
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret == "ALTER TABLE `category` ADD `name` VARCHAR(200) NOT NULL"
    else:
        assert ret == 'ALTER TABLE "category" ADD "name" VARCHAR(200) NOT NULL'


def test_modify_column():
    if isinstance(Migrate.ddl, SqliteDDL):
        with pytest.raises(NotSupportError):
            ret0 = Migrate.ddl.modify_column(Category, Category._meta.fields_map.get("name"))
            ret1 = Migrate.ddl.modify_column(User, User._meta.fields_map.get("is_active"))

    else:
        ret0 = Migrate.ddl.modify_column(Category, Category._meta.fields_map.get("name"))
        ret1 = Migrate.ddl.modify_column(User, User._meta.fields_map.get("is_active"))
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret0 == "ALTER TABLE `category` MODIFY COLUMN `name` VARCHAR(200) NOT NULL"
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert ret0 == 'ALTER TABLE "category" ALTER COLUMN "name" TYPE VARCHAR(200)'

    if isinstance(Migrate.ddl, MysqlDDL):
        assert (
            ret1
            == "ALTER TABLE `user` MODIFY COLUMN `is_active` BOOL NOT NULL  COMMENT 'Is Active' DEFAULT 1"
        )
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert ret1 == 'ALTER TABLE "user" ALTER COLUMN "is_active" TYPE BOOL'


def test_rename_column():
    if isinstance(Migrate.ddl, SqliteDDL):
        with pytest.raises(NotSupportError):
            ret0 = Migrate.ddl.rename_column(
                Category, "name", Category._meta.fields_map.get("name")
            )
    else:
        ret0 = Migrate.ddl.rename_column(
            Category, "old_name", Category._meta.fields_map.get("name")
        )
        ret1 = Migrate.ddl.rename_column(
            User, "old_is_active", User._meta.fields_map.get("is_active")
        )
        if isinstance(Migrate.ddl, MysqlDDL):
            assert ret0 == "ALTER TABLE `category` CHANGE `old_name` `name` VARCHAR(200) NOT NULL"
        elif isinstance(Migrate.ddl, PostgresDDL):
            assert ret0 == 'ALTER TABLE "category" RENAME COLUMN "old_name" TO "name"'
        if isinstance(Migrate.ddl, MysqlDDL):
            assert (
                ret1
                == "ALTER TABLE `user` CHANGE `old_is_active` `is_active` BOOL NOT NULL  COMMENT 'Is Active' DEFAULT 1"
            )
        elif isinstance(Migrate.ddl, PostgresDDL):
            assert ret1 == 'ALTER TABLE "user" RENAME COLUMN "old_is_active" TO "is_active"'


def test_alter_column_default():
    ret = Migrate.ddl.alter_column_default(Category, Category._meta.fields_map.get("name"))
    if isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'ALTER TABLE "category" ALTER COLUMN "name" DROP DEFAULT'
    else:
        assert ret is None

    ret = Migrate.ddl.alter_column_default(Category, Category._meta.fields_map.get("created_at"))
    if isinstance(Migrate.ddl, PostgresDDL):
        assert (
            ret == 'ALTER TABLE "category" ALTER COLUMN "created_at" SET DEFAULT CURRENT_TIMESTAMP'
        )
    else:
        assert ret is None

    ret = Migrate.ddl.alter_column_default(User, User._meta.fields_map.get("avatar"))
    if isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'ALTER TABLE "user" ALTER COLUMN "avatar" SET DEFAULT \'\''
    else:
        assert ret is None


def test_alter_column_null():
    ret = Migrate.ddl.alter_column_null(Category, Category._meta.fields_map.get("name"))
    if isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'ALTER TABLE "category" ALTER COLUMN "name" SET NOT NULL'
    else:
        assert ret is None


def test_set_comment():
    ret = Migrate.ddl.set_comment(Category, Category._meta.fields_map.get("name"))
    if isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'COMMENT ON COLUMN "category"."name" IS NULL'
    else:
        assert ret is None

    ret = Migrate.ddl.set_comment(Category, Category._meta.fields_map.get("user"))
    if isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'COMMENT ON COLUMN "category"."user" IS \'User\''
    else:
        assert ret is None


def test_drop_column():
    if isinstance(Migrate.ddl, SqliteDDL):
        with pytest.raises(NotSupportError):
            ret = Migrate.ddl.drop_column(Category, "name")
    else:
        ret = Migrate.ddl.drop_column(Category, "name")
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret == "ALTER TABLE `category` DROP COLUMN `name`"
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'ALTER TABLE "category" DROP COLUMN "name"'


def test_add_index():
    index = Migrate.ddl.add_index(Category, ["name"])
    index_u = Migrate.ddl.add_index(Category, ["name"], True)
    if isinstance(Migrate.ddl, MysqlDDL):
        assert index == "ALTER TABLE `category` ADD  INDEX `idx_category_name_8b0cb9` (`name`)"
        assert (
            index_u == "ALTER TABLE `category` ADD UNIQUE INDEX `uid_category_name_8b0cb9` (`name`)"
        )
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert index == 'CREATE INDEX "idx_category_name_8b0cb9" ON "category" ("name")'
        assert (
            index_u
            == 'ALTER TABLE "category" ADD CONSTRAINT "uid_category_name_8b0cb9" UNIQUE ("name")'
        )
    else:
        assert index == 'ALTER TABLE "category" ADD  INDEX "idx_category_name_8b0cb9" ("name")'
        assert (
            index_u == 'ALTER TABLE "category" ADD UNIQUE INDEX "uid_category_name_8b0cb9" ("name")'
        )


def test_drop_index():
    ret = Migrate.ddl.drop_index(Category, ["name"])
    ret_u = Migrate.ddl.drop_index(Category, ["name"], True)
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret == "ALTER TABLE `category` DROP INDEX `idx_category_name_8b0cb9`"
        assert ret_u == "ALTER TABLE `category` DROP INDEX `uid_category_name_8b0cb9`"
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'DROP INDEX "idx_category_name_8b0cb9"'
        assert ret_u == 'ALTER TABLE "category" DROP CONSTRAINT "uid_category_name_8b0cb9"'
    else:
        assert ret == 'ALTER TABLE "category" DROP INDEX "idx_category_name_8b0cb9"'
        assert ret_u == 'ALTER TABLE "category" DROP INDEX "uid_category_name_8b0cb9"'


def test_add_fk():
    ret = Migrate.ddl.add_fk(Category, Category._meta.fields_map.get("user"))
    if isinstance(Migrate.ddl, MysqlDDL):
        assert (
            ret
            == "ALTER TABLE `category` ADD CONSTRAINT `fk_category_user_e2e3874c` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE"
        )
    else:
        assert (
            ret
            == 'ALTER TABLE "category" ADD CONSTRAINT "fk_category_user_e2e3874c" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE'
        )


def test_drop_fk():
    ret = Migrate.ddl.drop_fk(Category, Category._meta.fields_map.get("user"))
    if isinstance(Migrate.ddl, MysqlDDL):
        assert ret == "ALTER TABLE `category` DROP FOREIGN KEY `fk_category_user_e2e3874c`"
    elif isinstance(Migrate.ddl, PostgresDDL):
        assert ret == 'ALTER TABLE "category" DROP CONSTRAINT "fk_category_user_e2e3874c"'
    else:
        assert ret == 'ALTER TABLE "category" DROP FOREIGN KEY "fk_category_user_e2e3874c"'
