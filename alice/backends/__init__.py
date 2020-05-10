from typing import Type

from tortoise import Model, BaseDBAsyncClient
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class DDL:
    schema_generator_cls: Type[BaseSchemaGenerator] = BaseSchemaGenerator

    def __init__(self, client: "BaseDBAsyncClient", model: "Type[Model]"):
        self.model = model
        self.schema_generator = self.schema_generator_cls(client)

    def create_table(self):
        return self.schema_generator._get_table_sql(self.model, True)['table_creation_string']

    def drop_table(self):
        return f'drop table {self.model._meta.db_table}'

    def add_column(self):
        raise NotImplementedError()

    def drop_column(self):
        raise NotImplementedError()

    def add_index(self):
        raise NotImplementedError()

    def drop_index(self):
        raise NotImplementedError()

    def add_fk(self):
        raise NotImplementedError()

    def drop_fk(self):
        raise NotImplementedError()
