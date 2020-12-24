from typing import List, Optional

from ddlparse import DdlParse
from tortoise import BaseDBAsyncClient
from tortoise.backends.mysql.client import MySQLSchemaGenerator


class InspectDb:
    def __init__(self, conn: BaseDBAsyncClient, tables: Optional[List[str]] = None):
        self.conn = conn
        self.tables = tables
        self.DIALECT = conn.schema_generator.DIALECT

    async def show_create_tables(self):
        if self.DIALECT == MySQLSchemaGenerator.DIALECT:
            if not self.tables:
                sql_tables = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{self.conn.database}';"
                ret = await self.conn.execute_query(sql_tables)
                self.tables = map(lambda x: x[0], ret)
            for table in self.tables:
                sql_show_create_table = f"SHOW CREATE TABLE {table}"
                ret = await self.conn.execute_query(sql_show_create_table)
                yield ret[1][0]["Create Table"]
        else:
            raise NotImplementedError("Currently only support MySQL")

    async def inspect(self):
        ddl_list = self.show_create_tables()
        async for ddl in ddl_list:
            parser = DdlParse(ddl, DdlParse.DATABASE.mysql)
            table = parser.parse()
            print(table)
