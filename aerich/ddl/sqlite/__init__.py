from typing import Type

from tortoise import Model
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator

from aerich.ddl import BaseDDL
from aerich.exceptions import NotSupportError


class SqliteDDL(BaseDDL):
    schema_generator_cls = SqliteSchemaGenerator
    DIALECT = SqliteSchemaGenerator.DIALECT

    def drop_column(self, model: "Type[Model]", column_name: str):
        raise NotSupportError("Drop column is unsupported in SQLite.")

    def modify_column(self, model: "Type[Model]", field_object: dict, is_pk: bool = True):
        raise NotSupportError("Modify column is unsupported in SQLite.")

    def alter_column_default(self, model: "Type[Model]", field_describe: dict):
        raise NotSupportError("Alter column default is unsupported in SQLite.")

    def alter_column_null(self, model: "Type[Model]", field_describe: dict):
        raise NotSupportError("Alter column null is unsupported in SQLite.")

    def set_comment(self, model: "Type[Model]", field_describe: dict):
        raise NotSupportError("Alter column comment is unsupported in SQLite.")
