from typing import List, Type

from tortoise import BaseDBAsyncClient, ForeignKeyFieldInstance, Model
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.fields import Field


class BaseDDL:
    schema_generator_cls: Type[BaseSchemaGenerator] = BaseSchemaGenerator
    DIALECT = "sql"
    _DROP_TABLE_TEMPLATE = "DROP TABLE {table_name} IF EXISTS"
    _ADD_COLUMN_TEMPLATE = "ALTER TABLE {table_name} ADD {column}"
    _DROP_COLUMN_TEMPLATE = "ALTER TABLE {table_name} DROP COLUMN {column_name}"
    _ADD_INDEX_TEMPLATE = (
        "ALTER TABLE {table_name} ADD {unique} INDEX {index_name} ({column_names})"
    )
    _DROP_INDEX_TEMPLATE = "ALTER TABLE {table_name} DROP INDEX {index_name}"
    _ADD_FK_TEMPLATE = "ALTER TABLE {table_name} ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{db_column}`) REFERENCES `{table}` (`{field}`) ON DELETE {on_delete}"
    _DROP_FK_TEMPLATE = "ALTER TABLE {table_name} DROP FOREIGN KEY {fk_name}"

    def __init__(self, client: "BaseDBAsyncClient"):
        self.client = client
        self.schema_generator = self.schema_generator_cls(client)

    def create_table(self, model: "Type[Model]"):
        raise NotImplementedError

    def drop_table(self, model: "Type[Model]"):
        raise NotImplementedError

    def add_column(self, model: "Type[Model]", field_object: Field):
        raise NotImplementedError

    def drop_column(self, model: "Type[Model]", column_name: str):
        raise NotImplementedError

    def add_index(self, model: "Type[Model]", field_names: List[str], unique=False):
        raise NotImplementedError

    def drop_index(self, model: "Type[Model]", field_names: List[str], unique=False):
        raise NotImplementedError

    def add_fk(self, model: "Type[Model]", field: ForeignKeyFieldInstance):
        raise NotImplementedError

    def drop_fk(self, model: "Type[Model]", field: ForeignKeyFieldInstance):
        raise NotImplementedError
