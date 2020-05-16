from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator

from aerich.ddl import BaseDDL


class MysqlDDL(BaseDDL):
    schema_generator_cls = MySQLSchemaGenerator
    DIALECT = MySQLSchemaGenerator.DIALECT
