from typing import List

from aerich.inspect import Column, Inspect


class InspectSQLite(Inspect):
    @property
    def field_map(self) -> dict:
        return {
            "INTEGER": self.int_field,
            "INT": self.bool_field,
            "SMALLINT": self.smallint_field,
            "VARCHAR": self.char_field,
            "TEXT": self.text_field,
            "TIMESTAMP": self.datetime_field,
            "REAL": self.float_field,
            "BIGINT": self.bigint_field,
            "DATE": self.date_field,
            "TIME": self.time_field,
            "JSON": self.json_field,
            "BLOB": self.binary_field,
        }

    async def get_columns(self, table: str) -> List[Column]:
        columns = []
        sql = f"PRAGMA table_info({table})"
        ret = await self.conn.execute_query_dict(sql)
        for row in ret:
            try:
                length = row["type"].split("(")[1].split(")")[0]
            except IndexError:
                length = None
            columns.append(
                Column(
                    name=row["name"],
                    data_type=row["type"].split("(")[0],
                    null=row["notnull"] == 0,
                    default=row["dflt_value"],
                    length=length,
                    pk=row["pk"] == 1,
                    unique=False,  # can't get this simply
                )
            )
        return columns

    async def get_all_tables(self) -> List[str]:
        sql = "select tbl_name from sqlite_master where type='table' and name!='sqlite_sequence'"
        ret = await self.conn.execute_query_dict(sql)
        return list(map(lambda x: x["tbl_name"], ret))
