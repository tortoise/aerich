import importlib
import os
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type, Union

import click
from dictdiffer import diff
from tortoise import BaseDBAsyncClient, Model, Tortoise
from tortoise.exceptions import OperationalError
from tortoise.indexes import Index

from aerich.ddl import BaseDDL
from aerich.models import MAX_VERSION_LENGTH, Aerich
from aerich.utils import get_app_connection, get_models_describe, is_default_function

MIGRATE_TEMPLATE = """from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return \"\"\"
        {upgrade_sql}\"\"\"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return \"\"\"
        {downgrade_sql}\"\"\"
"""


class Migrate:
    upgrade_operators: List[str] = []
    downgrade_operators: List[str] = []
    _upgrade_fk_m2m_index_operators: List[str] = []
    _downgrade_fk_m2m_index_operators: List[str] = []
    _upgrade_m2m: List[str] = []
    _downgrade_m2m: List[str] = []
    _aerich = Aerich.__name__
    _rename_old = []
    _rename_new = []

    ddl: BaseDDL
    _last_version_content: Optional[dict] = None
    app: str
    migrate_location: Path
    dialect: str
    _db_version: Optional[str] = None

    @classmethod
    def get_all_version_files(cls) -> List[str]:
        return sorted(
            filter(lambda x: x.endswith("py"), os.listdir(cls.migrate_location)),
            key=lambda x: int(x.split("_")[0]),
        )

    @classmethod
    def _get_model(cls, model: str) -> Type[Model]:
        return Tortoise.apps.get(cls.app).get(model)

    @classmethod
    async def get_last_version(cls) -> Optional[Aerich]:
        try:
            return await Aerich.filter(app=cls.app).first()
        except OperationalError:
            pass

    @classmethod
    async def _get_db_version(cls, connection: BaseDBAsyncClient):
        if cls.dialect == "mysql":
            sql = "select version() as version"
            ret = await connection.execute_query(sql)
            cls._db_version = ret[1][0].get("version")

    @classmethod
    async def load_ddl_class(cls):
        ddl_dialect_module = importlib.import_module(f"aerich.ddl.{cls.dialect}")
        return getattr(ddl_dialect_module, f"{cls.dialect.capitalize()}DDL")

    @classmethod
    async def init(cls, config: dict, app: str, location: str):
        await Tortoise.init(config=config)
        last_version = await cls.get_last_version()
        cls.app = app
        cls.migrate_location = Path(location, app)
        if last_version:
            cls._last_version_content = last_version.content

        connection = get_app_connection(config, app)
        cls.dialect = connection.schema_generator.DIALECT
        cls.ddl_class = await cls.load_ddl_class()
        cls.ddl = cls.ddl_class(connection)
        await cls._get_db_version(connection)

    @classmethod
    async def _get_last_version_num(cls):
        last_version = await cls.get_last_version()
        if not last_version:
            return None
        version = last_version.version
        return int(version.split("_", 1)[0])

    @classmethod
    async def generate_version(cls, name=None):
        now = datetime.now().strftime("%Y%m%d%H%M%S").replace("/", "")
        last_version_num = await cls._get_last_version_num()
        if last_version_num is None:
            return f"0_{now}_init.py"
        version = f"{last_version_num + 1}_{now}_{name}.py"
        if len(version) > MAX_VERSION_LENGTH:
            raise ValueError(f"Version name exceeds maximum length ({MAX_VERSION_LENGTH})")
        return version

    @classmethod
    async def _generate_diff_py(cls, name):
        version = await cls.generate_version(name)
        # delete if same version exists
        for version_file in cls.get_all_version_files():
            if version_file.startswith(version.split("_")[0]):
                os.unlink(Path(cls.migrate_location, version_file))

        version_file = Path(cls.migrate_location, version)
        content = cls._get_diff_file_content()

        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)
        return version

    @classmethod
    async def migrate(cls, name: str, empty: bool) -> str:
        """
        diff old models and new models to generate diff content
        :param name: str name for migration
        :param empty: bool if True generates empty migration
        :return:
        """
        if empty:
            return await cls._generate_diff_py(name)

        new_version_content = get_models_describe(cls.app)
        cls.diff_models(cls._last_version_content, new_version_content)
        cls.diff_models(new_version_content, cls._last_version_content, False)

        cls._merge_operators()

        if not cls.upgrade_operators:
            return ""

        return await cls._generate_diff_py(name)

    @classmethod
    def _get_diff_file_content(cls) -> str:
        """
        builds content for diff file from template
        """

        def join_lines(lines: List[str]) -> str:
            if not lines:
                return ""
            return ";\n        ".join(lines) + ";"

        return MIGRATE_TEMPLATE.format(
            upgrade_sql=join_lines(cls.upgrade_operators),
            downgrade_sql=join_lines(cls.downgrade_operators),
        )

    @classmethod
    def _add_operator(cls, operator: str, upgrade=True, fk_m2m_index=False):
        """
        add operator,differentiate fk because fk is order limit
        :param operator:
        :param upgrade:
        :param fk_m2m_index:
        :return:
        """
        operator = operator.rstrip(";")
        if upgrade:
            if fk_m2m_index:
                cls._upgrade_fk_m2m_index_operators.append(operator)
            else:
                cls.upgrade_operators.append(operator)
        else:
            if fk_m2m_index:
                cls._downgrade_fk_m2m_index_operators.append(operator)
            else:
                cls.downgrade_operators.append(operator)

    @classmethod
    def _handle_indexes(cls, model: Type[Model], indexes: List[Union[Tuple[str], Index]]):
        ret = []
        for index in indexes:
            if isinstance(index, Index):
                index.__hash__ = lambda self: md5(  # nosec: B303
                    self.index_name(cls.ddl.schema_generator, model).encode()
                    + self.__class__.__name__.encode()
                ).hexdigest()
            ret.append(index)
        return ret

    @classmethod
    def _return_order_m2ms(cls, old_m2m_fields, new_m2m_fields):
        """
        dictdiffer.diff: 当对象为list的时候，他的check是按照list索引check的，但是old_m2m_fields, new_m2m_fields两个list的顺序无法确定，因此这个函数将会按照
        through 作为关键字，进行list元素排序，现在你可以任意的添加和删除多对多关系的字段了

        dictdiffer.diff: When the objects are two lists, its check is checked according to the list index,
        but the order of the two lists cannot be determined, so this function will follow the `through`
        is used as the keyword to sort the list elements. Now you can add and delete fields of many-to-many
        relationship at will

        :param old_m2m_fields: aerich  old_m2m_fields
        :param new_m2m_fields: aerich  new_m2m_fields
        :return: 返回经过 through字段排序后的两个list
        """
        if len(old_m2m_fields) <= len(new_m2m_fields):
            # add or change
            new_list = ['' for i in range(len(old_m2m_fields))]
            old_m2m_fields_dict = {value['through']: str(index) for index, value in enumerate(old_m2m_fields)}

            for index, item in enumerate(new_m2m_fields):
                if old_m2m_fields_dict.get(item['through']):
                    new_list[int(old_m2m_fields_dict.get(item['through']))] = item
                else:
                    new_list.append(item)
            return old_m2m_fields, new_list
        else:
            # remove
            new_list = ['' for i in range(len(new_m2m_fields))]
            new_m2m_fields_dict = {value['through']: str(index) for index, value in enumerate(new_m2m_fields)}

            for index, item in enumerate(old_m2m_fields):
                if new_m2m_fields_dict.get(item['through']):
                    new_list[int(new_m2m_fields_dict.get(item['through']))] = item
                else:
                    new_list.append(item)
            return new_list, new_m2m_fields

    @classmethod
    def diff_models(cls, old_models: Dict[str, dict], new_models: Dict[str, dict], upgrade=True):
        """
        diff models and add operators
        :param old_models:
        :param new_models:
        :param upgrade:
        :return:
        """
        _aerich = f"{cls.app}.{cls._aerich}"
        old_models.pop(_aerich, None)
        new_models.pop(_aerich, None)

        for new_model_str, new_model_describe in new_models.items():
            model = cls._get_model(new_model_describe.get("name").split(".")[1])

            if new_model_str not in old_models.keys():
                if upgrade:
                    cls._add_operator(cls.add_model(model), upgrade)
                else:
                    # we can't find origin model when downgrade, so skip
                    pass
            else:
                old_model_describe = old_models.get(new_model_str)
                # rename table
                new_table = new_model_describe.get("table")
                old_table = old_model_describe.get("table")
                if new_table != old_table:
                    cls._add_operator(cls.rename_table(model, old_table, new_table), upgrade)
                old_unique_together = set(
                    map(lambda x: tuple(x), old_model_describe.get("unique_together"))
                )
                new_unique_together = set(
                    map(lambda x: tuple(x), new_model_describe.get("unique_together"))
                )
                old_indexes = set(
                    map(
                        lambda x: x if isinstance(x, Index) else tuple(x),
                        cls._handle_indexes(model, old_model_describe.get("indexes", [])),
                    )
                )
                new_indexes = set(
                    map(
                        lambda x: x if isinstance(x, Index) else tuple(x),
                        cls._handle_indexes(model, new_model_describe.get("indexes", [])),
                    )
                )
                old_pk_field = old_model_describe.get("pk_field")
                new_pk_field = new_model_describe.get("pk_field")
                # pk field
                changes = diff(old_pk_field, new_pk_field)
                for action, option, change in changes:
                    # current only support rename pk
                    if action == "change" and option == "name":
                        cls._add_operator(cls._rename_field(model, *change), upgrade)
                # m2m fields
                old_m2m_fields = old_model_describe.get("m2m_fields")
                new_m2m_fields = new_model_describe.get("m2m_fields")
                old_m2m_fields, new_m2m_fields = cls._return_order_m2ms(old_m2m_fields, new_m2m_fields)
                for action, option, change in diff(old_m2m_fields, new_m2m_fields):
                    if change[0][0] == "db_constraint":
                        continue
                    if isinstance(change[0][1], str):
                        for new_m2m_field in new_m2m_fields:
                            if new_m2m_field["name"] == change[0][1]:
                                table = new_m2m_field.get("through")
                                break
                    else:
                        table = change[0][1].get("through")
                    if action == "add":
                        add = False
                        if upgrade and table not in cls._upgrade_m2m:
                            cls._upgrade_m2m.append(table)
                            add = True
                        elif not upgrade and table not in cls._downgrade_m2m:
                            cls._downgrade_m2m.append(table)
                            add = True
                        if add:
                            cls._add_operator(
                                cls.create_m2m(
                                    model,
                                    change[0][1],
                                    new_models.get(change[0][1].get("model_name")),
                                ),
                                upgrade,
                                fk_m2m_index=True,
                            )
                    elif action == "remove":
                        add = False
                        if upgrade and table not in cls._upgrade_m2m:
                            cls._upgrade_m2m.append(table)
                            add = True
                        elif not upgrade and table not in cls._downgrade_m2m:
                            cls._downgrade_m2m.append(table)
                            add = True
                        if add:
                            cls._add_operator(cls.drop_m2m(table), upgrade, True)
                # add unique_together
                for index in new_unique_together.difference(old_unique_together):
                    cls._add_operator(cls._add_index(model, index, True), upgrade, True)
                # remove unique_together
                for index in old_unique_together.difference(new_unique_together):
                    cls._add_operator(cls._drop_index(model, index, True), upgrade, True)
                # add indexes
                for index in new_indexes.difference(old_indexes):
                    cls._add_operator(cls._add_index(model, index, False), upgrade, True)
                # remove indexes
                for index in old_indexes.difference(new_indexes):
                    cls._add_operator(cls._drop_index(model, index, False), upgrade, True)
                old_data_fields = list(
                    filter(
                        lambda x: x.get("db_field_types") is not None,
                        old_model_describe.get("data_fields"),
                    )
                )
                new_data_fields = list(
                    filter(
                        lambda x: x.get("db_field_types") is not None,
                        new_model_describe.get("data_fields"),
                    )
                )

                old_data_fields_name = list(map(lambda x: x.get("name"), old_data_fields))
                new_data_fields_name = list(map(lambda x: x.get("name"), new_data_fields))

                # add fields or rename fields
                for new_data_field_name in set(new_data_fields_name).difference(
                        set(old_data_fields_name)
                ):
                    new_data_field = next(
                        filter(lambda x: x.get("name") == new_data_field_name, new_data_fields)
                    )
                    is_rename = False
                    for old_data_field in old_data_fields:
                        changes = list(diff(old_data_field, new_data_field))
                        old_data_field_name = old_data_field.get("name")
                        if len(changes) == 2:
                            # rename field
                            if (
                                    changes[0]
                                    == (
                                    "change",
                                    "name",
                                    (old_data_field_name, new_data_field_name),
                            )
                                    and changes[1]
                                    == (
                                    "change",
                                    "db_column",
                                    (
                                            old_data_field.get("db_column"),
                                            new_data_field.get("db_column"),
                                    ),
                            )
                                    and old_data_field_name not in new_data_fields_name
                            ):
                                if upgrade:
                                    is_rename = click.prompt(
                                        f"Rename {old_data_field_name} to {new_data_field_name}?",
                                        default=True,
                                        type=bool,
                                        show_choices=True,
                                    )
                                else:
                                    is_rename = old_data_field_name in cls._rename_new
                                if is_rename:
                                    cls._rename_new.append(new_data_field_name)
                                    cls._rename_old.append(old_data_field_name)
                                    # only MySQL8+ has rename syntax
                                    if (
                                            cls.dialect == "mysql"
                                            and cls._db_version
                                            and cls._db_version.startswith("5.")
                                    ):
                                        cls._add_operator(
                                            cls._change_field(
                                                model, old_data_field, new_data_field
                                            ),
                                            upgrade,
                                        )
                                    else:
                                        cls._add_operator(
                                            cls._rename_field(model, *changes[1][2]),
                                            upgrade,
                                        )
                    if not is_rename:
                        cls._add_operator(
                            cls._add_field(
                                model,
                                new_data_field,
                            ),
                            upgrade,
                        )
                        if new_data_field["indexed"]:
                            cls._add_operator(
                                cls._add_index(
                                    model, {new_data_field["db_column"]}, new_data_field["unique"]
                                ),
                                upgrade,
                                True,
                            )
                # remove fields
                for old_data_field_name in set(old_data_fields_name).difference(
                        set(new_data_fields_name)
                ):
                    # don't remove field if is renamed
                    if (upgrade and old_data_field_name in cls._rename_old) or (
                            not upgrade and old_data_field_name in cls._rename_new
                    ):
                        continue
                    old_data_field = next(
                        filter(lambda x: x.get("name") == old_data_field_name, old_data_fields)
                    )
                    db_column = old_data_field["db_column"]
                    cls._add_operator(
                        cls._remove_field(
                            model,
                            db_column,
                        ),
                        upgrade,
                    )
                    if old_data_field["indexed"]:
                        cls._add_operator(
                            cls._drop_index(
                                model,
                                {db_column},
                            ),
                            upgrade,
                            True,
                        )

                old_fk_fields = old_model_describe.get("fk_fields")
                new_fk_fields = new_model_describe.get("fk_fields")

                old_fk_fields_name = list(map(lambda x: x.get("name"), old_fk_fields))
                new_fk_fields_name = list(map(lambda x: x.get("name"), new_fk_fields))

                # add fk
                for new_fk_field_name in set(new_fk_fields_name).difference(
                        set(old_fk_fields_name)
                ):
                    fk_field = next(
                        filter(lambda x: x.get("name") == new_fk_field_name, new_fk_fields)
                    )
                    if fk_field.get("db_constraint"):
                        cls._add_operator(
                            cls._add_fk(
                                model, fk_field, new_models.get(fk_field.get("python_type"))
                            ),
                            upgrade,
                            fk_m2m_index=True,
                        )
                # drop fk
                for old_fk_field_name in set(old_fk_fields_name).difference(
                        set(new_fk_fields_name)
                ):
                    old_fk_field = next(
                        filter(lambda x: x.get("name") == old_fk_field_name, old_fk_fields)
                    )
                    if old_fk_field.get("db_constraint"):
                        cls._add_operator(
                            cls._drop_fk(
                                model, old_fk_field, old_models.get(old_fk_field.get("python_type"))
                            ),
                            upgrade,
                            fk_m2m_index=True,
                        )
                # change fields
                for field_name in set(new_data_fields_name).intersection(set(old_data_fields_name)):
                    old_data_field = next(
                        filter(lambda x: x.get("name") == field_name, old_data_fields)
                    )
                    new_data_field = next(
                        filter(lambda x: x.get("name") == field_name, new_data_fields)
                    )
                    changes = diff(old_data_field, new_data_field)
                    modified = False
                    for change in changes:
                        _, option, old_new = change
                        if option == "indexed":
                            # change index
                            unique = new_data_field.get("unique")
                            if old_new[0] is False and old_new[1] is True:
                                cls._add_operator(
                                    cls._add_index(model, (field_name,), unique), upgrade, True
                                )
                            else:
                                cls._add_operator(
                                    cls._drop_index(model, (field_name,), unique), upgrade, True
                                )
                        elif option == "db_field_types.":
                            if new_data_field.get("field_type") == "DecimalField":
                                # modify column
                                cls._add_operator(
                                    cls._modify_field(model, new_data_field),
                                    upgrade,
                                )
                            else:
                                continue
                        elif option == "default":
                            if not (
                                    is_default_function(old_new[0]) or is_default_function(old_new[1])
                            ):
                                # change column default
                                cls._add_operator(
                                    cls._alter_default(model, new_data_field), upgrade
                                )
                        elif option == "unique":
                            # because indexed include it
                            continue
                        elif option == "nullable":
                            # change nullable
                            cls._add_operator(cls._alter_null(model, new_data_field), upgrade)
                        elif option == "description":
                            # change comment
                            cls._add_operator(cls._set_comment(model, new_data_field), upgrade)
                        else:
                            if modified:
                                continue
                            # modify column
                            cls._add_operator(
                                cls._modify_field(model, new_data_field),
                                upgrade,
                            )
                            modified = True

        for old_model in old_models:
            if old_model not in new_models.keys():
                cls._add_operator(cls.drop_model(old_models.get(old_model).get("table")), upgrade)

    @classmethod
    def rename_table(cls, model: Type[Model], old_table_name: str, new_table_name: str):
        return cls.ddl.rename_table(model, old_table_name, new_table_name)

    @classmethod
    def add_model(cls, model: Type[Model]):
        return cls.ddl.create_table(model)

    @classmethod
    def drop_model(cls, table_name: str):
        return cls.ddl.drop_table(table_name)

    @classmethod
    def create_m2m(cls, model: Type[Model], field_describe: dict, reference_table_describe: dict):
        return cls.ddl.create_m2m(model, field_describe, reference_table_describe)

    @classmethod
    def drop_m2m(cls, table_name: str):
        return cls.ddl.drop_m2m(table_name)

    @classmethod
    def _resolve_fk_fields_name(cls, model: Type[Model], fields_name: Tuple[str]):
        ret = []
        for field_name in fields_name:
            field = model._meta.fields_map[field_name]
            if field.source_field:
                ret.append(field.source_field)
            elif field_name in model._meta.fk_fields:
                ret.append(field_name + "_id")
            else:
                ret.append(field_name)
        return ret

    @classmethod
    def _drop_index(cls, model: Type[Model], fields_name: Union[Tuple[str], Index], unique=False):
        if isinstance(fields_name, Index):
            return cls.ddl.drop_index_by_name(
                model, fields_name.index_name(cls.ddl.schema_generator, model)
            )
        fields_name = cls._resolve_fk_fields_name(model, fields_name)
        return cls.ddl.drop_index(model, fields_name, unique)

    @classmethod
    def _add_index(cls, model: Type[Model], fields_name: Union[Tuple[str], Index], unique=False):
        if isinstance(fields_name, Index):
            return fields_name.get_sql(cls.ddl.schema_generator, model, False)
        fields_name = cls._resolve_fk_fields_name(model, fields_name)
        return cls.ddl.add_index(model, fields_name, unique)

    @classmethod
    def _add_field(cls, model: Type[Model], field_describe: dict, is_pk: bool = False):
        return cls.ddl.add_column(model, field_describe, is_pk)

    @classmethod
    def _alter_default(cls, model: Type[Model], field_describe: dict):
        return cls.ddl.alter_column_default(model, field_describe)

    @classmethod
    def _alter_null(cls, model: Type[Model], field_describe: dict):
        return cls.ddl.alter_column_null(model, field_describe)

    @classmethod
    def _set_comment(cls, model: Type[Model], field_describe: dict):
        return cls.ddl.set_comment(model, field_describe)

    @classmethod
    def _modify_field(cls, model: Type[Model], field_describe: dict):
        return cls.ddl.modify_column(model, field_describe)

    @classmethod
    def _drop_fk(cls, model: Type[Model], field_describe: dict, reference_table_describe: dict):
        return cls.ddl.drop_fk(model, field_describe, reference_table_describe)

    @classmethod
    def _remove_field(cls, model: Type[Model], column_name: str):
        return cls.ddl.drop_column(model, column_name)

    @classmethod
    def _rename_field(cls, model: Type[Model], old_field_name: str, new_field_name: str):
        return cls.ddl.rename_column(model, old_field_name, new_field_name)

    @classmethod
    def _change_field(cls, model: Type[Model], old_field_describe: dict, new_field_describe: dict):
        db_field_types = new_field_describe.get("db_field_types")
        return cls.ddl.change_column(
            model,
            old_field_describe.get("db_column"),
            new_field_describe.get("db_column"),
            db_field_types.get(cls.dialect) or db_field_types.get(""),
        )

    @classmethod
    def _add_fk(cls, model: Type[Model], field_describe: dict, reference_table_describe: dict):
        """
        add fk
        :param model:
        :param field_describe:
        :param reference_table_describe:
        :return:
        """
        return cls.ddl.add_fk(model, field_describe, reference_table_describe)

    @classmethod
    def _merge_operators(cls):
        """
        fk/m2m/index must be last when add,first when drop
        :return:
        """
        for _upgrade_fk_m2m_operator in cls._upgrade_fk_m2m_index_operators:
            if "ADD" in _upgrade_fk_m2m_operator or "CREATE" in _upgrade_fk_m2m_operator:
                cls.upgrade_operators.append(_upgrade_fk_m2m_operator)
            else:
                cls.upgrade_operators.insert(0, _upgrade_fk_m2m_operator)

        for _downgrade_fk_m2m_operator in cls._downgrade_fk_m2m_index_operators:
            if "ADD" in _downgrade_fk_m2m_operator or "CREATE" in _downgrade_fk_m2m_operator:
                cls.downgrade_operators.append(_downgrade_fk_m2m_operator)
            else:
                cls.downgrade_operators.insert(0, _downgrade_fk_m2m_operator)
