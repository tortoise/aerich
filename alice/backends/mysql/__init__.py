from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator

from alice.backends import DDL


class MysqlDDL(DDL):
    schema_generator_cls = MySQLSchemaGenerator

    def drop_table(self):
        pass

    def add_column(self):
        pass

    def drop_column(self):
        pass

    def add_index(self):
        pass

    def drop_index(self):
        pass

    def add_fk(self):
        pass

    def drop_fk(self):
        pass
