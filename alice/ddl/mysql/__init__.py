from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator

from alice.ddl import DDL


class MysqlDDL(DDL):
    schema_generator_cls = MySQLSchemaGenerator
    DIALECT = MySQLSchemaGenerator.DIALECT
