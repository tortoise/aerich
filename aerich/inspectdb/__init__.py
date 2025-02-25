from __future__ import annotations

import contextlib
from typing import Any, Callable, Dict, TypedDict

from pydantic import BaseModel
from tortoise import BaseDBAsyncClient


class ColumnInfoDict(TypedDict):
    name: str
    pk: str
    index: str
    null: str
    default: str
    length: str
    comment: str


# TODO: use dict to replace typing.Dict when dropping support for Python3.8
FieldMapDict = Dict[str, Callable[..., str]]


class Column(BaseModel):
    name: str
    data_type: str
    null: bool
    default: Any
    comment: str | None = None
    pk: bool
    unique: bool
    index: bool
    length: int | None = None
    extra: str | None = None
    decimal_places: int | None = None
    max_digits: int | None = None

    def translate(self) -> ColumnInfoDict:
        comment = default = length = index = null = pk = ""
        if self.pk:
            pk = "primary_key=True, "
        else:
            if self.unique:
                index = "unique=True, "
            elif self.index:
                index = "db_index=True, "
        if self.data_type in ("varchar", "VARCHAR"):
            length = f"max_length={self.length}, "
        elif self.data_type in ("decimal", "numeric"):
            length_parts = []
            if self.max_digits:
                length_parts.append(f"max_digits={self.max_digits}")
            if self.decimal_places:
                length_parts.append(f"decimal_places={self.decimal_places}")
            if length_parts:
                length = ", ".join(length_parts) + ", "
        if self.null:
            null = "null=True, "
        if self.default is not None and not self.pk:
            if self.data_type in ("tinyint", "INT"):
                default = f"default={'True' if self.default == '1' else 'False'}, "
            elif self.data_type == "bool":
                default = f"default={'True' if self.default == 'true' else 'False'}, "
            elif self.data_type in ("datetime", "timestamptz", "TIMESTAMP"):
                if self.default == "CURRENT_TIMESTAMP":
                    if self.extra == "DEFAULT_GENERATED on update CURRENT_TIMESTAMP":
                        default = "auto_now=True, "
                    else:
                        default = "auto_now_add=True, "
            else:
                if "::" in self.default:
                    default = f"default={self.default.split('::')[0]}, "
                elif self.default.endswith("()"):
                    default = ""
                elif self.default == "":
                    default = 'default=""'
                else:
                    default = f"default={self.default}, "

        if self.comment:
            comment = f"description='{self.comment}', "
        return {
            "name": self.name,
            "pk": pk,
            "index": index,
            "null": null,
            "default": default,
            "length": length,
            "comment": comment,
        }


class Inspect:
    _table_template = "class {table}(Model):\n"

    def __init__(self, conn: BaseDBAsyncClient, tables: list[str] | None = None) -> None:
        self.conn = conn
        with contextlib.suppress(AttributeError):
            self.database = conn.database  # type:ignore[attr-defined]
        self.tables = tables

    @property
    def field_map(self) -> FieldMapDict:
        raise NotImplementedError

    async def inspect(self) -> str:
        if not self.tables:
            self.tables = await self.get_all_tables()
        result = "from tortoise import Model, fields\n\n\n"
        tables = []
        for table in self.tables:
            columns = await self.get_columns(table)
            fields = []
            model = self._table_template.format(table=table.title().replace("_", ""))
            for column in columns:
                field = self.field_map[column.data_type](**column.translate())
                fields.append("    " + field)
            tables.append(model + "\n".join(fields))
        return result + "\n\n\n".join(tables)

    async def get_columns(self, table: str) -> list[Column]:
        raise NotImplementedError

    async def get_all_tables(self) -> list[str]:
        raise NotImplementedError

    @staticmethod
    def get_field_string(
        field_class: str, arguments: str = "{null}{default}{comment}", **kwargs
    ) -> str:
        name = kwargs["name"]
        field_params = arguments.format(**kwargs).strip().rstrip(",")
        return f"{name} = fields.{field_class}({field_params})"

    @classmethod
    def decimal_field(cls, **kwargs) -> str:
        return cls.get_field_string("DecimalField", **kwargs)

    @classmethod
    def time_field(cls, **kwargs) -> str:
        return cls.get_field_string("TimeField", **kwargs)

    @classmethod
    def date_field(cls, **kwargs) -> str:
        return cls.get_field_string("DateField", **kwargs)

    @classmethod
    def float_field(cls, **kwargs) -> str:
        return cls.get_field_string("FloatField", **kwargs)

    @classmethod
    def datetime_field(cls, **kwargs) -> str:
        return cls.get_field_string("DatetimeField", **kwargs)

    @classmethod
    def text_field(cls, **kwargs) -> str:
        return cls.get_field_string("TextField", **kwargs)

    @classmethod
    def char_field(cls, **kwargs) -> str:
        arguments = "{pk}{index}{length}{null}{default}{comment}"
        return cls.get_field_string("CharField", arguments, **kwargs)

    @classmethod
    def int_field(cls, field_class="IntField", **kwargs) -> str:
        arguments = "{pk}{index}{default}{comment}"
        return cls.get_field_string(field_class, arguments, **kwargs)

    @classmethod
    def smallint_field(cls, **kwargs) -> str:
        return cls.int_field("SmallIntField", **kwargs)

    @classmethod
    def bigint_field(cls, **kwargs) -> str:
        return cls.int_field("BigIntField", **kwargs)

    @classmethod
    def bool_field(cls, **kwargs) -> str:
        return cls.get_field_string("BooleanField", **kwargs)

    @classmethod
    def uuid_field(cls, **kwargs) -> str:
        arguments = "{pk}{index}{default}{comment}"
        return cls.get_field_string("UUIDField", arguments, **kwargs)

    @classmethod
    def json_field(cls, **kwargs) -> str:
        return cls.get_field_string("JSONField", **kwargs)

    @classmethod
    def binary_field(cls, **kwargs) -> str:
        return cls.get_field_string("BinaryField", **kwargs)
