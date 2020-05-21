import json
import os
import re
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Tuple, Type

from tortoise import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    Model,
    Tortoise,
)
from tortoise.fields import Field

from aerich.ddl import BaseDDL
from aerich.models import Aerich
from aerich.utils import get_app_connection


class Migrate:
    upgrade_operators: List[str] = []
    downgrade_operators: List[str] = []
    _upgrade_fk_m2m_index_operators: List[str] = []
    _downgrade_fk_m2m_index_operators: List[str] = []
    _upgrade_m2m: List[str] = []
    _downgrade_m2m: List[str] = []

    ddl: BaseDDL
    migrate_config: dict
    old_models = "old_models"
    diff_app = "diff_models"
    app: str
    migrate_location: str

    @classmethod
    def get_old_model_file(cls):
        return cls.old_models + ".py"

    @classmethod
    def get_all_version_files(cls) -> List[str]:
        return sorted(filter(lambda x: x.endswith("json"), os.listdir(cls.migrate_location)))

    @classmethod
    async def get_last_version(cls) -> Aerich:
        return await Aerich.filter(app=cls.app).first()

    @classmethod
    async def init_with_old_models(cls, config: dict, app: str, location: str):
        migrate_config = cls._get_migrate_config(config, app, location)

        cls.app = app
        cls.migrate_config = migrate_config
        cls.migrate_location = os.path.join(location, app)

        await Tortoise.init(config=migrate_config)

        connection = get_app_connection(config, app)
        if connection.schema_generator.DIALECT == "mysql":
            from aerich.ddl.mysql import MysqlDDL

            cls.ddl = MysqlDDL(connection)
        elif connection.schema_generator.DIALECT == "sqlite":
            from aerich.ddl.sqlite import SqliteDDL

            cls.ddl = SqliteDDL(connection)
        elif connection.schema_generator.DIALECT == "postgres":
            from aerich.ddl.postgres import PostgresDDL

            cls.ddl = PostgresDDL(connection)
        else:
            raise NotImplementedError("Current only support MySQL")

    @classmethod
    async def _get_last_version_num(cls):
        last_version = await cls.get_last_version()
        if not last_version:
            return 0
        version = last_version.version
        return version.split("_")[0]

    @classmethod
    async def _generate_diff_sql(cls, name):
        now = datetime.now().strftime("%Y%M%D%H%M%S").replace("/", "")
        last_version_num = await cls._get_last_version_num()
        version = f"{last_version_num + 1}_{now}_{name}.json"
        content = {
            "upgrade": cls.upgrade_operators,
            "downgrade": cls.downgrade_operators,
        }
        with open(os.path.join(cls.migrate_location, version), "w") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
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

        cls._diff_models(diff_models, app_models)
        cls._diff_models(app_models, diff_models, False)

        cls._merge_operators()

        if not cls.upgrade_operators:
            return ""

        return await cls._generate_diff_sql(name)

    @classmethod
    def _add_operator(cls, operator: str, upgrade=True, fk=False):
        """
        add operator,differentiate fk because fk is order limit
        :param operator:
        :param upgrade:
        :param fk_m2m:
        :return:
        """
        if upgrade:
            if fk:
                cls._upgrade_fk_m2m_index_operators.append(operator)
            else:
                cls.upgrade_operators.append(operator)
        else:
            if fk:
                cls._downgrade_fk_m2m_index_operators.append(operator)
            else:
                cls.downgrade_operators.append(operator)

    @classmethod
    def cp_models(
        cls, app: str, model_files: List[str], old_model_file,
    ):
        """
        cp currents models to old_model_files
        :param app:
        :param model_files:
        :param old_model_file:
        :return:
        """
        pattern = rf"(\n)?('|\")({app})(.\w+)('|\")"
        for i, model_file in enumerate(model_files):
            with open(model_file, "r") as f:
                content = f.read()
            ret = re.sub(pattern, rf"\2{cls.diff_app}\4\5", content)
            mode = "w" if i == 0 else "a"
            with open(old_model_file, mode) as f:
                f.write(ret)

    @classmethod
    def _get_migrate_config(cls, config: dict, app: str, location: str):
        """
        generate tmp config with old models
        :param config:
        :param app:
        :param location:
        :return:
        """
        temp_config = deepcopy(config)
        path = os.path.join(location, app, cls.old_models)
        path = path.replace("/", ".").lstrip(".")
        temp_config["apps"][cls.diff_app] = {"models": [path]}
        return temp_config

    @classmethod
    def write_old_models(cls, config: dict, app: str, location: str):
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
            old_model_files.append(model.replace(".", "/") + ".py")

        cls.cp_models(app, old_model_files, os.path.join(location, app, cls.get_old_model_file()))

    @classmethod
    def _diff_models(
        cls, old_models: Dict[str, Type[Model]], new_models: Dict[str, Type[Model]], upgrade=True
    ):
        """
        diff models and add operators
        :param old_models:
        :param new_models:
        :param upgrade:
        :return:
        """
        for new_model_str, new_model in new_models.items():
            if new_model_str not in old_models.keys():
                cls._add_operator(cls.add_model(new_model), upgrade)
            else:
                cls.diff_model(old_models.get(new_model_str), new_model, upgrade)

        for old_model in old_models:
            if old_model not in new_models.keys():
                cls._add_operator(cls.remove_model(old_models.get(old_model)), upgrade)

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
                cls._add_operator(
                    cls._add_field(new_model, new_field),
                    upgrade,
                    isinstance(new_field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)),
                )
            else:
                old_field = old_fields_map.get(new_key)
                if (old_field.index and not new_field.index) or (
                    old_field.unique and not new_field.unique
                ):
                    cls._add_operator(
                        cls._remove_index(
                            old_model, (old_field.model_field_name,), old_field.unique
                        ),
                        upgrade,
                        isinstance(old_field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)),
                    )
                elif (new_field.index and not old_field.index) or (
                    new_field.unique and not old_field.unique
                ):
                    cls._add_operator(
                        cls._add_index(new_model, (new_field.model_field_name,), new_field.unique),
                        upgrade,
                        isinstance(new_field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)),
                    )

        for old_key in old_keys:
            field = old_fields_map.get(old_key)
            if old_key not in new_keys and not cls._exclude_field(field, upgrade):
                cls._add_operator(
                    cls._remove_field(old_model, field),
                    upgrade,
                    isinstance(field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)),
                )

        for new_index in new_indexes:
            if new_index not in old_indexes:
                cls._add_operator(cls._add_index(new_model, new_index,), upgrade)
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
    def _remove_field(cls, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            return cls.ddl.drop_fk(model, field)
        if isinstance(field, ManyToManyFieldInstance):
            return cls.ddl.drop_m2m(field)
        return cls.ddl.drop_column(model, field.model_field_name)

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
