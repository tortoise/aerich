from typing import List, Type

from tortoise import ForeignKeyFieldInstance, Model
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.fields import Field, JSONField, TextField, UUIDField

from aerich.ddl import BaseDDL


class MysqlDDL(BaseDDL):
    schema_generator_cls = MySQLSchemaGenerator
    DIALECT = MySQLSchemaGenerator.DIALECT

    def create_table(self, model: "Type[Model]"):
        return self.schema_generator._get_table_sql(model, True)["table_creation_string"]

    def drop_table(self, model: "Type[Model]"):
        return self._DROP_TABLE_TEMPLATE.format(table_name=model._meta.db_table)

    def add_column(self, model: "Type[Model]", field_object: Field):
        db_table = model._meta.db_table
        default = field_object.default
        db_column = field_object.model_field_name
        auto_now_add = getattr(field_object, "auto_now_add", False)
        auto_now = getattr(field_object, "auto_now", False)
        if default is not None or auto_now_add:
            if callable(default) or isinstance(field_object, (UUIDField, TextField, JSONField)):
                default = ""
            else:
                default = field_object.to_db_value(default, model)
                try:
                    default = self.schema_generator._column_default_generator(
                        db_table,
                        db_column,
                        self.schema_generator._escape_default_value(default),
                        auto_now_add,
                        auto_now,
                    )
                except NotImplementedError:
                    default = ""
        else:
            default = ""
        return self._ADD_COLUMN_TEMPLATE.format(
            table_name=db_table,
            column=self.schema_generator._create_string(
                db_column=field_object.model_field_name,
                field_type=field_object.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                nullable="NOT NULL" if not field_object.null else "",
                unique="UNIQUE" if field_object.unique else "",
                comment=self.schema_generator._column_comment_generator(
                    table=db_table,
                    column=field_object.model_field_name,
                    comment=field_object.description,
                )
                if field_object.description
                else "",
                is_primary_key=field_object.pk,
                default=default,
            ),
        )

    def drop_column(self, model: "Type[Model]", column_name: str):
        return self._DROP_COLUMN_TEMPLATE.format(
            table_name=model._meta.db_table, column_name=column_name
        )

    def add_index(self, model: "Type[Model]", field_names: List[str], unique=False):
        return self._ADD_INDEX_TEMPLATE.format(
            unique="UNIQUE" if unique else "",
            index_name=self.schema_generator._generate_index_name(
                "idx" if not unique else "uid", model, field_names
            ),
            table_name=model._meta.db_table,
            column_names=", ".join([self.schema_generator.quote(f) for f in field_names]),
        )

    def drop_index(self, model: "Type[Model]", field_names: List[str], unique=False):
        return self._DROP_INDEX_TEMPLATE.format(
            index_name=self.schema_generator._generate_index_name(
                "idx" if not unique else "uid", model, field_names
            ),
            table_name=model._meta.db_table,
        )

    def add_fk(self, model: "Type[Model]", field: ForeignKeyFieldInstance):
        db_table = model._meta.db_table
        to_field_name = field.to_field_instance.source_field
        if not to_field_name:
            to_field_name = field.to_field_instance.model_field_name

        db_column = field.source_field or field.model_field_name + "_id"
        fk_name = self.schema_generator._generate_fk_name(
            from_table=db_table,
            from_field=db_column,
            to_table=field.related_model._meta.db_table,
            to_field=to_field_name,
        )
        return self._ADD_FK_TEMPLATE.format(
            table_name=db_table,
            fk_name=fk_name,
            db_column=db_column,
            table=field.related_model._meta.db_table,
            field=to_field_name,
            on_delete=field.on_delete,
        )

    def drop_fk(self, model: "Type[Model]", field: ForeignKeyFieldInstance):
        to_field_name = field.to_field_instance.source_field
        if not to_field_name:
            to_field_name = field.to_field_instance.model_field_name
        db_table = model._meta.db_table
        return self._DROP_FK_TEMPLATE.format(
            table_name=db_table,
            fk_name=self.schema_generator._generate_fk_name(
                from_table=db_table,
                from_field=field.source_field or field.model_field_name + "_id",
                to_table=field.related_model._meta.db_table,
                to_field=to_field_name,
            ),
        )
