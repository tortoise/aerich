from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator

from aerich.ddl import BaseDDL


class PostgresDDL(BaseDDL):
    schema_generator_cls = AsyncpgSchemaGenerator
    DIALECT = AsyncpgSchemaGenerator.DIALECT
