import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

import click
from tortoise import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    BaseDBAsyncClient,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    Model,
    Tortoise,
)
from tortoise.exceptions import OperationalError
from tortoise.fields import Field

from aerich.ddl import BaseDDL
from aerich.models import MAX_VERSION_LENGTH, Aerich
from aerich.utils import get_app_connection, get_models_describe, write_version_file


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
    migrate_location: str
    dialect: str
    _db_version: Optional[str] = None

    @classmethod
    def get_all_version_files(cls) -> List[str]:
        return sorted(
            filter(lambda x: x.endswith("sql"), os.listdir(cls.migrate_location)),
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
    async def init(cls, config: dict, app: str, location: str):
        await Tortoise.init(config=config)
        last_version = await cls.get_last_version()
        cls.app = app
        cls.migrate_location = Path(location, app)
        if last_version:
            cls._last_version_content = last_version.content

        connection = get_app_connection(config, app)
        cls.dialect = connection.schema_generator.DIALECT
        if cls.dialect == "mysql":
            from aerich.ddl.mysql import MysqlDDL

            cls.ddl = MysqlDDL(connection)
        elif cls.dialect == "sqlite":
            from aerich.ddl.sqlite import SqliteDDL

            cls.ddl = SqliteDDL(connection)
        elif cls.dialect == "postgres":
            from aerich.ddl.postgres import PostgresDDL

            cls.ddl = PostgresDDL(connection)
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
            return f"0_{now}_init.sql"
        version = f"{last_version_num + 1}_{now}_{name}.sql"
        if len(version) > MAX_VERSION_LENGTH:
            raise ValueError(f"Version name exceeds maximum length ({MAX_VERSION_LENGTH})")
        return version

    @classmethod
    async def _generate_diff_sql(cls, name):
        version = await cls.generate_version(name)
        # delete if same version exists
        for version_file in cls.get_all_version_files():
            if version_file.startswith(version.split("_")[0]):
                os.unlink(Path(cls.migrate_location, version_file))
        content = {
            "upgrade": cls.upgrade_operators,
            "downgrade": cls.downgrade_operators,
        }
        write_version_file(Path(cls.migrate_location, version), content)
        return version

    @classmethod
    async def migrate(cls, name) -> str:
        """
        diff old models and new models to generate diff content
        :param name:
        :return:
        """
        new_version_content = get_models_describe(cls.app)
        cls.diff_models(cls._last_version_content, new_version_content)
        cls.diff_models(new_version_content, cls._last_version_content, False)

        cls._merge_operators()

        if not cls.upgrade_operators:
            return ""

        return await cls._generate_diff_sql(name)

    @classmethod
    def _add_operator(cls, operator: str, upgrade=True, fk_m2m=False):
        """
        add operator,differentiate fk because fk is order limit
        :param operator:
        :param upgrade:
        :param fk_m2m:
        :return:
        """
        if upgrade:
            if fk_m2m:
                cls._upgrade_fk_m2m_index_operators.append(operator)
            else:
                cls.upgrade_operators.append(operator)
        else:
            if fk_m2m:
                cls._downgrade_fk_m2m_index_operators.append(operator)
            else:
                cls.downgrade_operators.append(operator)

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
            if new_model_str not in old_models.keys():
                cls._add_operator(cls.add_model(cls._get_model(new_model_str)), upgrade)
            else:
                cls.diff_model(old_models.get(new_model_str), new_model_describe, upgrade)

        for old_model in old_models:
            if old_model not in new_models.keys():
                cls._add_operator(cls.remove_model(cls._get_model(old_model)), upgrade)

    @classmethod
    def _is_fk_m2m(cls, field: Field):
        return isinstance(field, (ForeignKeyFieldInstance, ManyToManyFieldInstance))

    @classmethod
    def add_model(cls, model: Type[Model]):
        return cls.ddl.create_table(model)

    @classmethod
    def remove_model(cls, model: Type[Model]):
        return cls.ddl.drop_table(model)

    @classmethod
    def diff_model(cls, old_model_describe: dict, new_model_describe: dict, upgrade=True):
        """
        diff single model
        :param old_model_describe:
        :param new_model_describe:
        :param upgrade:
        :return:
        """

        old_unique_together = old_model_describe.get('unique_together')
        new_unique_together = new_model_describe.get('unique_together')

        old_data_fields = old_model_describe.get('data_fields')
        new_data_fields = new_model_describe.get('data_fields')

        old_data_fields_name = list(map(lambda x: x.get('name'), old_data_fields))
        new_data_fields_name = list(map(lambda x: x.get('name'), new_data_fields))

        model = cls._get_model(new_model_describe.get('name').split('.')[1])
        # add fields
        for new_data_field_name in set(new_data_fields_name).difference(set(old_data_fields_name)):
            cls._add_operator(
                cls._add_field(model, next(filter(lambda x: x.get('name') == new_data_field_name, new_data_fields))),
                upgrade)
        # remove fields
        for old_data_field_name in set(old_data_fields_name).difference(set(new_data_fields_name)):
            cls._add_operator(
                cls._remove_field(model, next(filter(lambda x: x.get('name') == old_data_field_name, old_data_fields))),
                upgrade)

        old_fk_fields = old_model_describe.get('fk_fields')
        new_fk_fields = new_model_describe.get('fk_fields')

        old_fk_fields_name = list(map(lambda x: x.get('name'), old_fk_fields))
        new_fk_fields_name = list(map(lambda x: x.get('name'), new_fk_fields))

        # add fk
        for new_fk_field_name in set(new_fk_fields_name).difference(set(old_fk_fields_name)):
            fk_field = next(filter(lambda x: x.get('name') == new_fk_field_name, new_fk_fields))
            cls._add_operator(
                cls._add_fk(model, fk_field,
                            next(filter(lambda x: x.get('db_column') == fk_field.get('raw_field'), new_data_fields))),
                upgrade)
        # drop fk
        for old_fk_field_name in set(old_fk_fields_name).difference(set(new_fk_fields_name)):
            old_fk_field = next(filter(lambda x: x.get('name') == old_fk_field_name, old_fk_fields))
            cls._add_operator(
                cls._drop_fk(
                    model, old_fk_field,
                    next(filter(lambda x: x.get('db_column') == old_fk_field.get('raw_field'), old_data_fields))),
                upgrade)

    @classmethod
    def _resolve_fk_fields_name(cls, model: Type[Model], fields_name: Tuple[str]):
        ret = []
        for field_name in fields_name:
            if field_name in model._meta.fk_fields:
                ret.append(field_name + "_id")
            else:
                ret.append(field_name)
        return ret

    @classmethod
    def _remove_index(cls, model: Type[Model], fields_name: Tuple[str], unique=False):
        fields_name = cls._resolve_fk_fields_name(model, fields_name)
        return cls.ddl.drop_index(model, fields_name, unique)

    @classmethod
    def _add_index(cls, model: Type[Model], fields_name: Tuple[str], unique=False):
        fields_name = cls._resolve_fk_fields_name(model, fields_name)
        return cls.ddl.add_index(model, fields_name, unique)

    @classmethod
    def _exclude_field(cls, field: Field, upgrade=False):
        """
        exclude BackwardFKRelation and repeat m2m field
        :param field:
        :return:
        """
        if isinstance(field, ManyToManyFieldInstance):
            through = field.through
            if upgrade:
                if through in cls._upgrade_m2m:
                    return True
                else:
                    cls._upgrade_m2m.append(through)
                    return False
            else:
                if through in cls._downgrade_m2m:
                    return True
                else:
                    cls._downgrade_m2m.append(through)
                    return False
        return isinstance(field, (BackwardFKRelation, BackwardOneToOneRelation))

    @classmethod
    def _add_field(cls, model: Type[Model], field_describe: dict, is_pk: bool = False):
        return cls.ddl.add_column(model, field_describe, is_pk)

    @classmethod
    def _alter_default(cls, model: Type[Model], field: Field):
        return cls.ddl.alter_column_default(model, field)

    @classmethod
    def _alter_null(cls, model: Type[Model], field: Field):
        return cls.ddl.alter_column_null(model, field)

    @classmethod
    def _set_comment(cls, model: Type[Model], field: Field):
        return cls.ddl.set_comment(model, field)

    @classmethod
    def _modify_field(cls, model: Type[Model], field: Field):
        return cls.ddl.modify_column(model, field)

    @classmethod
    def _drop_fk(cls, model: Type[Model], field_describe: dict, field_describe_target: dict):
        return cls.ddl.drop_fk(model, field_describe, field_describe_target)

    @classmethod
    def _remove_field(cls, model: Type[Model], field_describe: dict):
        return cls.ddl.drop_column(model, field_describe)

    @classmethod
    def _rename_field(cls, model: Type[Model], old_field: Field, new_field: Field):
        return cls.ddl.rename_column(model, old_field.model_field_name, new_field.model_field_name)

    @classmethod
    def _change_field(cls, model: Type[Model], old_field: Field, new_field: Field):
        return cls.ddl.change_column(
            model,
            old_field.model_field_name,
            new_field.model_field_name,
            new_field.get_for_dialect(cls.dialect, "SQL_TYPE"),
        )

    @classmethod
    def _add_fk(cls, model: Type[Model], field_describe: dict, field_describe_target: dict):
        """
        add fk
        :param model:
        :param field:
        :return:
        """
        return cls.ddl.add_fk(model, field_describe, field_describe_target)

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
