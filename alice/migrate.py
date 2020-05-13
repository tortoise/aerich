import importlib
import inspect
from typing import List, Type, Dict

from tortoise import Model, ForeignKeyFieldInstance
from tortoise.fields import Field

from alice.backends import DDL


class Migrate:
    operators: List
    ddl: DDL

    def __init__(self, ddl: DDL):
        self.operators = []
        self.ddl = ddl

    def diff_models_module(self, old_models_module, new_models_module):
        old_module = importlib.import_module(old_models_module)
        old_models = {}
        new_models = {}
        for name, obj in inspect.getmembers(old_module):
            if inspect.isclass(obj) and issubclass(obj, Model):
                old_models[obj.__name__] = obj

        new_module = importlib.import_module(new_models_module)
        for name, obj in inspect.getmembers(new_module):
            if inspect.isclass(obj) and issubclass(obj, Model):
                new_models[obj.__name__] = obj
        self.diff_models(old_models, new_models)

    def diff_models(self, old_models: Dict[str, Type[Model]], new_models: Dict[str, Type[Model]]):
        for new_model_str, new_model in new_models.items():
            if new_model_str not in old_models.keys():
                self.add_model(new_model)
            else:
                self.diff_model(old_models.get(new_model_str), new_model)

        for old_model in old_models:
            if old_model not in new_models.keys():
                self.remove_model(old_models.get(old_model))

    def _add_operator(self, operator):
        self.operators.append(operator)

    def add_model(self, model: Type[Model]):
        self._add_operator(self.ddl.create_table(model))

    def remove_model(self, model: Type[Model]):
        self._add_operator(self.ddl.drop_table(model))

    def diff_model(self, old_model: Type[Model], new_model: Type[Model]):
        old_fields_map = old_model._meta.fields_map
        new_fields_map = new_model._meta.fields_map
        old_keys = old_fields_map.keys()
        new_keys = new_fields_map.keys()
        for new_key in new_keys:
            new_field = new_fields_map.get(new_key)
            if new_key not in old_keys:
                self._add_field(new_model, new_field)
            else:
                old_field = old_fields_map.get(new_key)
                if old_field.index and not new_field.index:
                    self._remove_index(old_model, old_field)
                elif new_field.index and not old_field.index:
                    self._add_index(new_model, new_field)
        for old_key in old_keys:
            if old_key not in new_keys:
                field = old_fields_map.get(old_key)
                self._remove_field(old_model, field)

    def _remove_index(self, model: Type[Model], field: Field):
        self._add_operator(self.ddl.drop_index(model, [field.model_field_name], field.unique))

    def _add_index(self, model: Type[Model], field: Field):
        self._add_operator(self.ddl.add_index(model, [field.model_field_name], field.unique))

    def _add_field(self, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            self._add_operator(self.ddl.add_fk(model, field))
        else:
            self._add_operator(self.ddl.add_column(model, field))

    def _remove_field(self, model: Type[Model], field: Field):
        if isinstance(field, ForeignKeyFieldInstance):
            self._add_operator(self.ddl.drop_fk(model, field))
        self._add_operator(self.ddl.drop_column(model, field.model_field_name))
