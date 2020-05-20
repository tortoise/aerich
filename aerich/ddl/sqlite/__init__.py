from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator

from aerich.ddl import BaseDDL


class SqliteDDL(BaseDDL):
    schema_generator_cls = SqliteSchemaGenerator
    DIALECT = SqliteSchemaGenerator.DIALECT
