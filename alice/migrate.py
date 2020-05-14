import json
import os
import re
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Type

from tortoise import ForeignKeyFieldInstance, Model, Tortoise
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.fields import Field

from alice.ddl import DDL
from alice.ddl.mysql import MysqlDDL
from alice.exceptions import ConfigurationError
from alice.utils import get_app_connection


class Migrate:
    upgrade_operators: List[str] = []
    downgrade_operators: List[str] = []
    ddl: DDL
    migrate_config: dict
    old_models = "old_models"
    diff_app = "diff_models"
    app: str
    migrate_location: str

    @classmethod
    def get_old_model_file(cls):
        return cls.old_models + ".py"

    @classmethod
    def _get_all_migrate_files(cls):
        return sorted(filter(lambda x: x.endswith("json"), os.listdir(cls.migrate_location)))

    @classmethod
    def _get_latest_version(cls) -> int:
        ret = cls._get_all_migrate_files()
        if ret:
            return int(ret[-1].split("_")[0])
        return 0

    @classmethod
    def get_all_version_files(cls, is_all=True):
        files = cls._get_all_migrate_files()
        ret = []
        for file in files:
            with open(os.path.join(cls.migrate_location, file), "r") as f:
                content = json.load(f)
                if is_all or not content.get("migrate"):
                    ret.append(file)
        return ret

    @classmethod
    async def init_with_old_models(cls, config: dict, app: str, location: str):
        migrate_config = cls._get_migrate_config(config, app, location)

        cls.app = app
        cls.migrate_config = migrate_config
        cls.migrate_location = os.path.join(location, app)

        await Tortoise.init(config=migrate_config)

        connection = get_app_connection(config, app)
        if connection.schema_generator is MySQLSchemaGenerator:
            cls.ddl = MysqlDDL(connection)
        else:
            raise NotImplementedError("Current only support MySQL")

    @classmethod
    def _generate_diff_sql(cls, name):
        now = datetime.now().strftime("%Y%M%D%H%M%S").replace("/", "")
        filename = f"{cls._get_latest_version() + 1}_{now}_{name}.json"
        content = {
            "upgrade": cls.upgrade_operators,
            "download": cls.downgrade_operators,
            "migrate": False,
        }
        with open(os.path.join(cls.migrate_location, filename), "w") as f:
            json.dump(content, f, indent=4)
        return filename

    @classmethod
    def migrate(cls, name):
        if not cls.migrate_config:
            raise ConfigurationError("You must call init_with_old_models() first!")
        apps = Tortoise.apps
        diff_models = apps.get(cls.diff_app)
        app_models = apps.get(cls.app)

        cls._diff_models(diff_models, app_models)
        cls._diff_models(app_models, diff_models, False)

        if not cls.upgrade_operators:
            return False

        return cls._generate_diff_sql(name)

    @classmethod
    def _add_operator(cls, operator: str, upgrade=True):
        if upgrade:
            cls.upgrade_operators.append(operator)
        else:
            cls.downgrade_operators.append(operator)

    @classmethod
    def cp_models(
            cls, model_files: List[str], old_model_file,
    ):
        """
        cp currents models to old_model_files
        :param model_files:
        :param old_model_file:
        :return:
        """
        pattern = (
            r"(ManyToManyField|ForeignKeyField|OneToOneField)\((model_name)?(\"|\')(\w+)(.+)\)"
        )
        for i, model_file in enumerate(model_files):
            with open(model_file, "r") as f:
                content = f.read()
            ret = re.sub(pattern, rf"\1\2(\3{cls.diff_app}\5)", content)
            with open(old_model_file, "w" if i == 0 else "w+a") as f:
                f.write(ret)

    @classmethod
    def _get_migrate_config(cls, config: dict, app: str, location: str):
        temp_config = deepcopy(config)
        path = os.path.join(location, app, cls.old_models)
        path = path.replace("/", ".").lstrip(".")
        temp_config["apps"][cls.diff_app] = {"models": [path]}
        return temp_config

    @classmethod
    def write_old_models(cls, config: dict, app: str, location: str):
        old_model_files = []
        models = config.get("apps").get(app).get("models")
        for model in models:
            old_model_files.append(model.replace(".", "/") + ".py")

        cls.cp_models(old_model_files, os.path.join(location, app, cls.get_old_model_file()))

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
        old_fields_map = old_model._meta.fields_map
        new_fields_map = new_model._meta.fields_map
        old_keys = old_fields_map.keys()
        new_keys = new_fields_map.keys()
        for new_key in new_keys:
            new_field = new_fields_map.get(new_key)
            if new_key not in old_keys:
                cls._add_operator(cls._add_field(new_model, new_field), upgrade)
            else:
                old_field = old_fields_map.get(new_key)
                if old_field.index and not new_field.index:
                    cls._add_operator(cls._remove_index(old_model, old_field), upgrade)
                elif new_field.index and not old_field.index:
                    cls._add_operator(cls._add_index(new_model, new_field), upgrade)
        for old_key in old_keys:
            if old_key not in new_keys:
                field = old_fields_map.get(old_key)
                cls._add_operator(cls._remove_field(old_model, field), upgrade)

    @classmethod
    def _remove_index(cls, model: Type[Model], field: Field):
        return cls.ddl.drop_index(model, [field.model_field_name], field.unique)

    @classmethod
    def _add_index(cls, model: Type[Model], field: Field):
        return cls.ddl.add_index(model, [field.model_field_name], field.unique)

    @classmethod
    def _add_field(cls, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            return cls.ddl.add_fk(model, field)
        else:
            return cls.ddl.add_column(model, field)

    @classmethod
    def _remove_field(cls, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            return cls.ddl.drop_fk(model, field)
        return cls.ddl.drop_column(model, field.model_field_name)
