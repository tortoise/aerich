import inspect
import os
import re
from datetime import datetime
from importlib import import_module
from io import StringIO
from typing import Dict, List, Optional, Tuple, Type, Union

import click
from packaging import version
from packaging.version import LegacyVersion, Version
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
from aerich.utils import get_app_connection, write_version_file


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
    migrate_config: dict
    old_models = "old_models"
    diff_app = "diff_models"
    app: str
    migrate_location: str
    dialect: str
    _db_version: Union[LegacyVersion, Version] = None

    @classmethod
    def get_old_model_file(cls, app: str, location: str):
        return os.path.join(location, app, cls.old_models + ".py")

    @classmethod
    def get_all_version_files(cls) -> List[str]:
        return sorted(
            filter(lambda x: x.endswith("sql"), os.listdir(cls.migrate_location)),
            key=lambda x: int(x.split("_")[0]),
        )

    @classmethod
    async def get_last_version(cls) -> Optional[Aerich]:
        try:
            return await Aerich.filter(app=cls.app).first()
        except OperationalError:
            pass

    @classmethod
    def remove_old_model_file(cls, app: str, location: str):
        try:
            os.unlink(cls.get_old_model_file(app, location))
        except (OSError, FileNotFoundError):
            pass

    @classmethod
    async def _get_db_version(cls, connection: BaseDBAsyncClient):
        if cls.dialect == "mysql":
            sql = "select version() as version"
            ret = await connection.execute_query(sql)
            cls._db_version = version.parse(ret[1][0].get("version"))

    @classmethod
    async def init_with_old_models(cls, config: dict, app: str, location: str):
        await Tortoise.init(config=config)
        last_version = await cls.get_last_version()
        cls.app = app
        cls.migrate_location = os.path.join(location, app)
        if last_version:
            content = last_version.content
            with open(cls.get_old_model_file(app, location), "w", encoding="utf-8") as f:
                f.write(content)

            migrate_config = cls._get_migrate_config(config, app, location)
            cls.migrate_config = migrate_config
            await Tortoise.init(config=migrate_config)

        connection = get_app_connection(config, app)
        if cls.dialect == "mysql":
            from aerich.ddl.mysql import MysqlDDL

            cls.ddl = MysqlDDL(connection)
        elif cls.dialect == "sqlite":
            from aerich.ddl.sqlite import SqliteDDL

            cls.ddl = SqliteDDL(connection)
        elif cls.dialect == "postgres":
            from aerich.ddl.postgres import PostgresDDL

            cls.ddl = PostgresDDL(connection)
        cls.dialect = cls.ddl.DIALECT
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
                os.unlink(os.path.join(cls.migrate_location, version_file))
        content = {
            "upgrade": cls.upgrade_operators,
            "downgrade": cls.downgrade_operators,
        }
        write_version_file(os.path.join(cls.migrate_location, version), content)
        return version

    @classmethod
    async def migrate(cls, name) -> str:
        """
        diff old models and new models to generate diff content
        :param name:
        :return:
        """
        apps = Tortoise.apps
        diff_models = apps.get(cls.diff_app)
        app_models = apps.get(cls.app)

        cls.diff_models(diff_models, app_models)
        cls.diff_models(app_models, diff_models, False)

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
    def _get_migrate_config(cls, config: dict, app: str, location: str):
        """
        generate tmp config with old models
        :param config:
        :param app:
        :param location:
        :return:
        """
        path = os.path.join(location, app, cls.old_models)
        path = path.replace(os.sep, ".").lstrip(".")
        config["apps"][cls.diff_app] = {
            "models": [path],
            "default_connection": config.get("apps").get(app).get("default_connection", "default"),
        }
        return config

    @classmethod
    def get_models_content(cls, config: dict, app: str, location: str):
        """
        write new models to old models
        :param config:
        :param app:
        :param location:
        :return:
        """
        old_model_files = []
        models = config.get("apps").get(app).get("models")
        for model in models:
            module = import_module(model)
            possible_models = [getattr(module, attr_name) for attr_name in dir(module)]
            for attr in filter(
                lambda x: inspect.isclass(x) and issubclass(x, Model) and x is not Model,
                possible_models,
            ):
                file = inspect.getfile(attr)
                if file not in old_model_files:
                    old_model_files.append(file)
        pattern = rf"(\n)?('|\")({app})(.\w+)('|\")"
        str_io = StringIO()
        for i, model_file in enumerate(old_model_files):
            with open(model_file, "r", encoding="utf-8") as f:
                content = f.read()
            ret = re.sub(pattern, rf"\2{cls.diff_app}\4\5", content)
            str_io.write(f"{ret}\n")
        return str_io.getvalue()

    @classmethod
    def diff_models(
        cls, old_models: Dict[str, Type[Model]], new_models: Dict[str, Type[Model]], upgrade=True
    ):
        """
        diff models and add operators
        :param old_models:
        :param new_models:
        :param upgrade:
        :return:
        """
        old_models.pop(cls._aerich, None)
        new_models.pop(cls._aerich, None)

        for new_model_str, new_model in new_models.items():
            if new_model_str not in old_models.keys():
                cls._add_operator(cls.add_model(new_model), upgrade)
            else:
                cls.diff_model(old_models.get(new_model_str), new_model, upgrade)

        for old_model in old_models:
            if old_model not in new_models.keys():
                cls._add_operator(cls.remove_model(old_models.get(old_model)), upgrade)

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
    def diff_model(cls, old_model: Type[Model], new_model: Type[Model], upgrade=True):
        """
        diff single model
        :param old_model:
        :param new_model:
        :param upgrade:
        :return:
        """
        old_indexes = old_model._meta.indexes
        new_indexes = new_model._meta.indexes

        old_unique_together = old_model._meta.unique_together
        new_unique_together = new_model._meta.unique_together

        old_fields_map = old_model._meta.fields_map
        new_fields_map = new_model._meta.fields_map

        old_keys = old_fields_map.keys()
        new_keys = new_fields_map.keys()
        for new_key in new_keys:
            new_field = new_fields_map.get(new_key)
            if cls._exclude_field(new_field, upgrade):
                continue
            if new_key not in old_keys:
                new_field_dict = new_field.describe(serializable=True)
                new_field_dict.pop("name", None)
                new_field_dict.pop("db_column", None)
                for diff_key in old_keys - new_keys:
                    old_field = old_fields_map.get(diff_key)
                    old_field_dict = old_field.describe(serializable=True)
                    old_field_dict.pop("name", None)
                    old_field_dict.pop("db_column", None)
                    if old_field_dict == new_field_dict:
                        if upgrade:
                            is_rename = click.prompt(
                                f"Rename {diff_key} to {new_key}?",
                                default=True,
                                type=bool,
                                show_choices=True,
                            )
                            cls._rename_new.append(new_key)
                            cls._rename_old.append(diff_key)
                        else:
                            is_rename = diff_key in cls._rename_new
                        if is_rename:
                            if (
                                cls.dialect == "mysql"
                                and cls._db_version
                                and cls._db_version.major == 5
                            ):
                                cls._add_operator(
                                    cls._change_field(new_model, old_field, new_field),
                                    upgrade,
                                )
                            else:
                                cls._add_operator(
                                    cls._rename_field(new_model, old_field, new_field),
                                    upgrade,
                                )
                            break
                else:
                    cls._add_operator(
                        cls._add_field(new_model, new_field),
                        upgrade,
                        cls._is_fk_m2m(new_field),
                    )
            else:
                old_field = old_fields_map.get(new_key)
                new_field_dict = new_field.describe(serializable=True)
                new_field_dict.pop("unique")
                new_field_dict.pop("indexed")
                old_field_dict = old_field.describe(serializable=True)
                old_field_dict.pop("unique")
                old_field_dict.pop("indexed")
                if not cls._is_fk_m2m(new_field) and new_field_dict != old_field_dict:
                    if cls.dialect == "postgres":
                        if new_field.null != old_field.null:
                            cls._add_operator(
                                cls._alter_null(new_model, new_field), upgrade=upgrade
                            )
                        if new_field.default != old_field.default and not callable(
                            new_field.default
                        ):
                            cls._add_operator(
                                cls._alter_default(new_model, new_field), upgrade=upgrade
                            )
                        if new_field.description != old_field.description:
                            cls._add_operator(
                                cls._set_comment(new_model, new_field), upgrade=upgrade
                            )
                        if new_field.field_type != old_field.field_type:
                            cls._add_operator(
                                cls._modify_field(new_model, new_field), upgrade=upgrade
                            )
                    else:
                        cls._add_operator(cls._modify_field(new_model, new_field), upgrade=upgrade)
                if (old_field.index and not new_field.index) or (
                    old_field.unique and not new_field.unique
                ):
                    cls._add_operator(
                        cls._remove_index(
                            old_model, (old_field.model_field_name,), old_field.unique
                        ),
                        upgrade,
                        cls._is_fk_m2m(old_field),
                    )
                elif (new_field.index and not old_field.index) or (
                    new_field.unique and not old_field.unique
                ):
                    cls._add_operator(
                        cls._add_index(new_model, (new_field.model_field_name,), new_field.unique),
                        upgrade,
                        cls._is_fk_m2m(new_field),
                    )
                if isinstance(new_field, ForeignKeyFieldInstance):
                    if old_field.db_constraint and not new_field.db_constraint:
                        cls._add_operator(
                            cls._drop_fk(new_model, new_field),
                            upgrade,
                            True,
                        )
                    if new_field.db_constraint and not old_field.db_constraint:
                        cls._add_operator(
                            cls._add_fk(new_model, new_field),
                            upgrade,
                            True,
                        )

        for old_key in old_keys:
            field = old_fields_map.get(old_key)
            if old_key not in new_keys and not cls._exclude_field(field, upgrade):
                if (upgrade and old_key not in cls._rename_old) or (
                    not upgrade and old_key not in cls._rename_new
                ):
                    cls._add_operator(
                        cls._remove_field(old_model, field),
                        upgrade,
                        cls._is_fk_m2m(field),
                    )

        for new_index in new_indexes:
            if new_index not in old_indexes:
                cls._add_operator(
                    cls._add_index(
                        new_model,
                        new_index,
                    ),
                    upgrade,
                )
        for old_index in old_indexes:
            if old_index not in new_indexes:
                cls._add_operator(cls._remove_index(old_model, old_index), upgrade)

        for new_unique in new_unique_together:
            if new_unique not in old_unique_together:
                cls._add_operator(cls._add_index(new_model, new_unique, unique=True), upgrade)

        for old_unique in old_unique_together:
            if old_unique not in new_unique_together:
                cls._add_operator(cls._remove_index(old_model, old_unique, unique=True), upgrade)

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
    def _add_field(cls, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            return cls.ddl.add_fk(model, field)
        if isinstance(field, ManyToManyFieldInstance):
            return cls.ddl.create_m2m_table(model, field)
        return cls.ddl.add_column(model, field)

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
    def _drop_fk(cls, model: Type[Model], field: ForeignKeyFieldInstance):
        return cls.ddl.drop_fk(model, field)

    @classmethod
    def _remove_field(cls, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            return cls.ddl.drop_fk(model, field)
        if isinstance(field, ManyToManyFieldInstance):
            return cls.ddl.drop_m2m(field)
        return cls.ddl.drop_column(model, field.model_field_name)

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
    def _add_fk(cls, model: Type[Model], field: ForeignKeyFieldInstance):
        """
        add fk
        :param model:
        :param field:
        :return:
        """
        return cls.ddl.add_fk(model, field)

    @classmethod
    def _remove_fk(cls, model: Type[Model], field: ForeignKeyFieldInstance):
        """
        drop fk
        :param model:
        :param field:
        :return:
        """
        return cls.ddl.drop_fk(model, field)

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
