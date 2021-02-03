from typing import List, Type

from tortoise import Model
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.fields import Field

from aerich.ddl import BaseDDL


class PostgresDDL(BaseDDL):
    schema_generator_cls = AsyncpgSchemaGenerator
    DIALECT = AsyncpgSchemaGenerator.DIALECT
    _ADD_INDEX_TEMPLATE = 'CREATE INDEX "{index_name}" ON "{table_name}" ({column_names})'
    _ADD_UNIQUE_TEMPLATE = (
        'ALTER TABLE "{table_name}" ADD CONSTRAINT "{index_name}" UNIQUE ({column_names})'
    )
    _DROP_INDEX_TEMPLATE = 'DROP INDEX "{index_name}"'
    _DROP_UNIQUE_TEMPLATE = 'ALTER TABLE "{table_name}" DROP CONSTRAINT "{index_name}"'
    _ALTER_NULL_TEMPLATE = 'ALTER TABLE "{table_name}" ALTER COLUMN "{column}" {set_drop} NOT NULL'
    _MODIFY_COLUMN_TEMPLATE = 'ALTER TABLE "{table_name}" ALTER COLUMN "{column}" TYPE {datatype}'
    _SET_COMMENT_TEMPLATE = 'COMMENT ON COLUMN "{table_name}"."{column}" IS {comment}'
    _DROP_FK_TEMPLATE = 'ALTER TABLE "{table_name}" DROP CONSTRAINT "{fk_name}"'

    def alter_column_null(self, model: "Type[Model]", field_describe: dict):
        db_table = model._meta.db_table
        return self._ALTER_NULL_TEMPLATE.format(
            table_name=db_table,
            column=field_describe.get("db_column"),
            set_drop="DROP" if field_describe.get("nullable") else "SET",
        )

    def modify_column(self, model: "Type[Model]", field_describe: dict, is_pk: bool = False):
        db_table = model._meta.db_table
        db_field_types = field_describe.get("db_field_types")
        return self._MODIFY_COLUMN_TEMPLATE.format(
            table_name=db_table,
            column=field_describe.get("db_column"),
            datatype=db_field_types.get(self.DIALECT) or db_field_types.get(""),
        )

    def add_index(self, model: "Type[Model]", field_names: List[str], unique=False):
        template = self._ADD_UNIQUE_TEMPLATE if unique else self._ADD_INDEX_TEMPLATE
        return template.format(
            index_name=self.schema_generator._generate_index_name(
                "uid" if unique else "idx", model, field_names
            ),
            table_name=model._meta.db_table,
            column_names=", ".join([self.schema_generator.quote(f) for f in field_names]),
        )

    def drop_index(self, model: "Type[Model]", field_names: List[str], unique=False):
        template = self._DROP_UNIQUE_TEMPLATE if unique else self._DROP_INDEX_TEMPLATE
        return template.format(
            index_name=self.schema_generator._generate_index_name(
                "uid" if unique else "idx", model, field_names
            ),
            table_name=model._meta.db_table,
        )

    def set_comment(self, model: "Type[Model]", field_object: Field):
        db_table = model._meta.db_table
        return self._SET_COMMENT_TEMPLATE.format(
            table_name=db_table,
            column=field_object.model_field_name,
            comment="'{}'".format(field_object.description) if field_object.description else "NULL",
        )
