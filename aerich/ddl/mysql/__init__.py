from typing import Type

from tortoise import Model
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator

from aerich.ddl import BaseDDL
from aerich.exceptions import NotSupportError


class MysqlDDL(BaseDDL):
    schema_generator_cls = MySQLSchemaGenerator
    DIALECT = MySQLSchemaGenerator.DIALECT
    _DROP_TABLE_TEMPLATE = "DROP TABLE IF EXISTS `{table_name}`"
    _ADD_COLUMN_TEMPLATE = "ALTER TABLE `{table_name}` ADD {column}"
    _ALTER_DEFAULT_TEMPLATE = "ALTER TABLE `{table_name}` ALTER COLUMN `{column}` {default}"
    _CHANGE_COLUMN_TEMPLATE = (
        "ALTER TABLE `{table_name}` CHANGE {old_column_name} {new_column_name} {new_column_type}"
    )
    _DROP_COLUMN_TEMPLATE = "ALTER TABLE `{table_name}` DROP COLUMN `{column_name}`"
    _RENAME_COLUMN_TEMPLATE = (
        "ALTER TABLE `{table_name}` RENAME COLUMN `{old_column_name}` TO `{new_column_name}`"
    )
    _ADD_INDEX_TEMPLATE = (
        "ALTER TABLE `{table_name}` ADD {unique}INDEX `{index_name}` ({column_names})"
    )
    _DROP_INDEX_TEMPLATE = "ALTER TABLE `{table_name}` DROP INDEX `{index_name}`"
    _ADD_FK_TEMPLATE = "ALTER TABLE `{table_name}` ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{db_column}`) REFERENCES `{table}` (`{field}`) ON DELETE {on_delete}"
    _DROP_FK_TEMPLATE = "ALTER TABLE `{table_name}` DROP FOREIGN KEY `{fk_name}`"
    _M2M_TABLE_TEMPLATE = "CREATE TABLE `{table_name}` (`{backward_key}` {backward_type} NOT NULL REFERENCES `{backward_table}` (`{backward_field}`) ON DELETE CASCADE,`{forward_key}` {forward_type} NOT NULL REFERENCES `{forward_table}` (`{forward_field}`) ON DELETE CASCADE){extra}{comment}"
    _MODIFY_COLUMN_TEMPLATE = "ALTER TABLE `{table_name}` MODIFY COLUMN {column}"

    def alter_column_null(self, model: "Type[Model]", field_describe: dict):
        raise NotSupportError("Alter column null is unsupported in MySQL.")

    def set_comment(self, model: "Type[Model]", field_describe: dict):
        raise NotSupportError("Alter column comment is unsupported in MySQL.")
