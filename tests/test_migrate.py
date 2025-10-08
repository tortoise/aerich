from __future__ import annotations

import shutil
from pathlib import Path

import anyio
import pytest
import tortoise
from pytest_mock import MockerFixture
from tortoise.indexes import Index

from aerich.ddl.mysql import MysqlDDL
from aerich.ddl.postgres import PostgresDDL
from aerich.ddl.sqlite import SqliteDDL
from aerich.exceptions import NotSupportError
from aerich.migrate import MIGRATE_TEMPLATE, Migrate
from aerich.models import Aerich
from aerich.utils import get_formatted_compressed_data, get_models_describe
from tests._utils import (
    chdir,
    describe_index,
    prepare_py_files,
    requires_dialect,
    run_shell,
    tmp_daily_db,
)
from tests.indexes import CustomIndex

# tortoise-orm>=0.21 changes IntField constraints
# from {"ge": 1, "le": 2147483647} to {"ge": -2147483648, "le": 2147483647}
MIN_INT = 1 if tortoise.__version__ < "0.21" else -2147483648
old_models_describe = {
    "models.Category": {
        "name": "models.Category",
        "app": "models",
        "table": "category",
        "abstract": False,
        "description": None,
        "docstring": None,
        "unique_together": [],
        "indexes": [describe_index(Index(fields=("slug",)))],
        "pk_field": {
            "name": "id",
            "field_type": "IntField",
            "db_column": "id",
            "python_type": "int",
            "generated": True,
            "nullable": False,
            "unique": True,
            "indexed": True,
            "default": None,
            "description": None,
            "docstring": None,
            "constraints": {"ge": MIN_INT, "le": 2147483647},
            "db_field_types": {"": "INT"},
        },
        "data_fields": [
            {
                "name": "slug",
                "field_type": "CharField",
                "db_column": "slug",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "name",
                "field_type": "CharField",
                "db_column": "name",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "created_at",
                "field_type": "DatetimeField",
                "db_column": "created_at",
                "python_type": "datetime.datetime",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"readOnly": True},
                "db_field_types": {
                    "": "TIMESTAMP",
                    "mysql": "DATETIME(6)",
                    "postgres": "TIMESTAMPTZ",
                },
                "auto_now_add": True,
                "auto_now": False,
            },
            {
                "name": "user_id",
                "field_type": "IntField",
                "db_column": "user_id",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": "User",
                "docstring": None,
                "constraints": {"ge": MIN_INT, "le": 2147483647},
                "db_field_types": {"": "INT"},
            },
            {
                "name": "title",
                "field_type": "CharField",
                "db_column": "title",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": True,
                "indexed": True,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 20},
                "db_field_types": {"": "VARCHAR(20)"},
            },
        ],
        "fk_fields": [
            {
                "name": "user",
                "field_type": "ForeignKeyFieldInstance",
                "python_type": "models.User",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": "User",
                "docstring": None,
                "constraints": {},
                "raw_field": "user_id",
                "on_delete": "CASCADE",
            }
        ],
        "backward_fk_fields": [],
        "o2o_fields": [],
        "backward_o2o_fields": [],
        "m2m_fields": [
            {
                "name": "products",
                "field_type": "ManyToManyFieldInstance",
                "python_type": "models.Product",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "model_name": "models.Product",
                "related_name": "categories",
                "forward_key": "product_id",
                "backward_key": "category_id",
                "through": "product_category",
                "on_delete": "CASCADE",
                "_generated": True,
            }
        ],
    },
    "models.Config": {
        "name": "models.Config",
        "app": "models",
        "table": "configs",
        "abstract": False,
        "description": None,
        "docstring": None,
        "unique_together": [],
        "indexes": [],
        "pk_field": {
            "name": "slug",
            "field_type": "CharField",
            "db_column": "slug",
            "python_type": "str",
            "generated": False,
            "nullable": False,
            "unique": True,
            "indexed": True,
            "default": None,
            "description": None,
            "docstring": None,
            "constraints": {"max_length": 10},
            "db_field_types": {"": "VARCHAR(10)"},
        },
        "data_fields": [
            {
                "name": "name",
                "field_type": "CharField",
                "db_column": "name",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": True,
                "indexed": True,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 100},
                "db_field_types": {"": "VARCHAR(100)"},
            },
            {
                "name": "label",
                "field_type": "CharField",
                "db_column": "label",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "key",
                "field_type": "CharField",
                "db_column": "key",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 20},
                "db_field_types": {"": "VARCHAR(20)"},
            },
            {
                "name": "value",
                "field_type": "JSONField",
                "db_column": "value",
                "python_type": "Union[dict, list]",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "db_field_types": {"": "TEXT", "postgres": "JSONB"},
            },
            {
                "name": "status",
                "field_type": "IntEnumFieldInstance",
                "db_column": "status",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": 1,
                "description": "on: 1\noff: 0",
                "docstring": None,
                "constraints": {"ge": -32768, "le": 32767},
                "db_field_types": {"": "SMALLINT"},
            },
        ],
        "fk_fields": [],
        "backward_fk_fields": [],
        "o2o_fields": [],
        "backward_o2o_fields": [],
        "m2m_fields": [
            {
                "name": "category",
                "field_type": "ManyToManyFieldInstance",
                "python_type": "models.Category",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "model_name": "models.Category",
                "related_name": "configs",
                "forward_key": "category_id",
                "backward_key": "config_id",
                "through": "config_category",
                "on_delete": "CASCADE",
                "_generated": False,
            },
            {
                "name": "categories",
                "field_type": "ManyToManyFieldInstance",
                "python_type": "models.Category",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "model_name": "models.Category",
                "related_name": "config_set",
                "forward_key": "category_id",
                "backward_key": "config_id",
                "through": "config_category_map",
                "on_delete": "CASCADE",
                "_generated": False,
            },
        ],
    },
    "models.Email": {
        "name": "models.Email",
        "app": "models",
        "table": "email",
        "abstract": False,
        "description": None,
        "docstring": None,
        "unique_together": [],
        "indexes": [],
        "pk_field": {
            "name": "id",
            "field_type": "IntField",
            "db_column": "id",
            "python_type": "int",
            "generated": True,
            "nullable": False,
            "unique": True,
            "indexed": True,
            "default": None,
            "description": None,
            "docstring": None,
            "constraints": {"ge": MIN_INT, "le": 2147483647},
            "db_field_types": {"": "INT"},
        },
        "data_fields": [
            {
                "name": "email",
                "field_type": "CharField",
                "db_column": "email",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "company",
                "field_type": "CharField",
                "db_column": "company",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": True,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 100},
                "db_field_types": {"": "VARCHAR(100)"},
            },
            {
                "name": "is_primary",
                "field_type": "BooleanField",
                "db_column": "is_primary",
                "python_type": "bool",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": False,
                "description": None,
                "docstring": None,
                "constraints": {},
                "db_field_types": {
                    "": "BOOL",
                    "mssql": "BIT",
                    "oracle": "NUMBER(1)",
                    "sqlite": "INT",
                },
            },
            {
                "name": "user_id",
                "field_type": "IntField",
                "db_column": "user_id",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"ge": MIN_INT, "le": 2147483647},
                "db_field_types": {"": "INT"},
            },
        ],
        "fk_fields": [
            {
                "name": "user",
                "field_type": "ForeignKeyFieldInstance",
                "python_type": "models.User",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "raw_field": "user_id",
                "on_delete": "CASCADE",
            }
        ],
        "backward_fk_fields": [],
        "o2o_fields": [],
        "backward_o2o_fields": [],
        "m2m_fields": [],
    },
    "models.Product": {
        "name": "models.Product",
        "app": "models",
        "table": "product",
        "abstract": False,
        "description": None,
        "docstring": None,
        "unique_together": [],
        "indexes": [],
        "pk_field": {
            "name": "id",
            "field_type": "IntField",
            "db_column": "id",
            "python_type": "int",
            "generated": True,
            "nullable": False,
            "unique": True,
            "indexed": True,
            "default": None,
            "description": None,
            "docstring": None,
            "constraints": {"ge": MIN_INT, "le": 2147483647},
            "db_field_types": {"": "INT"},
        },
        "data_fields": [
            {
                "name": "name",
                "field_type": "CharField",
                "db_column": "name",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 50},
                "db_field_types": {"": "VARCHAR(50)"},
            },
            {
                "name": "uid",
                "field_type": "IntField",
                "db_column": "uuid",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": True,
                "indexed": True,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"ge": -2147483648, "le": 2147483647},
                "db_field_types": {"": "INT"},
            },
            {
                "name": "view_num",
                "field_type": "IntField",
                "db_column": "view_num",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": "View Num",
                "docstring": None,
                "constraints": {"ge": -2147483648, "le": 2147483647},
                "db_field_types": {"": "INT"},
            },
            {
                "name": "sort",
                "field_type": "IntField",
                "db_column": "sort",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"ge": -2147483648, "le": 2147483647},
                "db_field_types": {"": "INT"},
            },
            {
                "name": "is_review",
                "field_type": "BooleanField",
                "db_column": "is_review",
                "python_type": "bool",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": "Is Reviewed",
                "docstring": None,
                "constraints": {},
                "db_field_types": {
                    "": "BOOL",
                    "mssql": "BIT",
                    "oracle": "NUMBER(1)",
                    "sqlite": "INT",
                },
            },
            {
                "name": "type",
                "field_type": "IntEnumFieldInstance",
                "db_column": "type_db_alias",
                "python_type": "int",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": "Product Type",
                "docstring": None,
                "constraints": {"ge": -32768, "le": 32767},
                "db_field_types": {"": "SMALLINT"},
            },
            {
                "name": "image",
                "field_type": "CharField",
                "db_column": "image",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "body",
                "field_type": "TextField",
                "db_column": "body",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "db_field_types": {"": "TEXT", "mysql": "LONGTEXT"},
            },
            {
                "name": "created_at",
                "field_type": "DatetimeField",
                "db_column": "created_at",
                "python_type": "datetime.datetime",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"readOnly": True},
                "db_field_types": {
                    "": "TIMESTAMP",
                    "mysql": "DATETIME(6)",
                    "postgres": "TIMESTAMPTZ",
                },
                "auto_now_add": True,
                "auto_now": False,
            },
            {
                "name": "is_delete",
                "field_type": "BooleanField",
                "db_column": "is_delete",
                "python_type": "bool",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": False,
                "description": None,
                "docstring": None,
                "constraints": {},
                "db_field_types": {
                    "": "BOOL",
                    "mssql": "BIT",
                    "oracle": "NUMBER(1)",
                    "sqlite": "INT",
                },
            },
        ],
        "fk_fields": [],
        "backward_fk_fields": [],
        "o2o_fields": [],
        "backward_o2o_fields": [],
        "m2m_fields": [
            {
                "name": "categories",
                "field_type": "ManyToManyFieldInstance",
                "python_type": "models.Category",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "model_name": "models.Category",
                "related_name": "products",
                "forward_key": "category_id",
                "backward_key": "product_id",
                "through": "product_category",
                "on_delete": "CASCADE",
                "_generated": False,
            }
        ],
    },
    "models.User": {
        "name": "models.User",
        "app": "models",
        "table": "user",
        "abstract": False,
        "description": None,
        "docstring": None,
        "unique_together": [],
        "indexes": [
            describe_index(Index(fields=("username", "is_active"))),
            describe_index(CustomIndex(fields=("is_superuser",))),
        ],
        "pk_field": {
            "name": "id",
            "field_type": "IntField",
            "db_column": "id",
            "python_type": "int",
            "generated": True,
            "nullable": False,
            "unique": True,
            "indexed": True,
            "default": None,
            "description": None,
            "docstring": None,
            "constraints": {"ge": MIN_INT, "le": 2147483647},
            "db_field_types": {"": "INT"},
        },
        "data_fields": [
            {
                "name": "username",
                "field_type": "CharField",
                "db_column": "username",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 20},
                "db_field_types": {"": "VARCHAR(20)"},
            },
            {
                "name": "password",
                "field_type": "CharField",
                "db_column": "password",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "last_login",
                "field_type": "DatetimeField",
                "db_column": "last_login",
                "python_type": "datetime.datetime",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": "<function None.now>",
                "description": "Last Login",
                "docstring": None,
                "constraints": {},
                "db_field_types": {
                    "": "TIMESTAMP",
                    "mysql": "DATETIME(6)",
                    "postgres": "TIMESTAMPTZ",
                },
                "auto_now_add": False,
                "auto_now": False,
            },
            {
                "name": "is_active",
                "field_type": "BooleanField",
                "db_column": "is_active",
                "python_type": "bool",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": True,
                "description": "Is Active",
                "docstring": None,
                "constraints": {},
                "db_field_types": {
                    "": "BOOL",
                    "mssql": "BIT",
                    "oracle": "NUMBER(1)",
                    "sqlite": "INT",
                },
            },
            {
                "name": "is_superuser",
                "field_type": "BooleanField",
                "db_column": "is_superuser",
                "python_type": "bool",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": False,
                "description": "Is SuperUser",
                "docstring": None,
                "constraints": {},
                "db_field_types": {
                    "": "BOOL",
                    "mssql": "BIT",
                    "oracle": "NUMBER(1)",
                    "sqlite": "INT",
                },
            },
            {
                "name": "avatar",
                "field_type": "CharField",
                "db_column": "avatar",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": "",
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 200},
                "db_field_types": {"": "VARCHAR(200)"},
            },
            {
                "name": "intro",
                "field_type": "TextField",
                "db_column": "intro",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": "",
                "description": None,
                "docstring": None,
                "constraints": {},
                "db_field_types": {"": "TEXT", "mysql": "LONGTEXT"},
            },
            {
                "name": "longitude",
                "unique": False,
                "default": None,
                "indexed": False,
                "nullable": False,
                "db_column": "longitude",
                "docstring": None,
                "generated": False,
                "field_type": "DecimalField",
                "constraints": {},
                "description": None,
                "python_type": "decimal.Decimal",
                "db_field_types": {"": "DECIMAL(12,9)", "sqlite": "VARCHAR(40)"},
            },
        ],
        "fk_fields": [],
        "backward_fk_fields": [
            {
                "name": "categorys",
                "field_type": "BackwardFKRelation",
                "python_type": "models.Category",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": "User",
                "docstring": None,
                "constraints": {},
            },
            {
                "name": "emails",
                "field_type": "BackwardFKRelation",
                "python_type": "models.Email",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
            },
        ],
        "o2o_fields": [],
        "backward_o2o_fields": [],
        "m2m_fields": [],
    },
    "models.Aerich": {
        "name": "models.Aerich",
        "app": "models",
        "table": "aerich",
        "abstract": False,
        "description": None,
        "docstring": None,
        "unique_together": [],
        "indexes": [],
        "pk_field": {
            "name": "id",
            "field_type": "IntField",
            "db_column": "id",
            "python_type": "int",
            "generated": True,
            "nullable": False,
            "unique": True,
            "indexed": True,
            "default": None,
            "description": None,
            "docstring": None,
            "constraints": {"ge": MIN_INT, "le": 2147483647},
            "db_field_types": {"": "INT"},
        },
        "data_fields": [
            {
                "name": "version",
                "field_type": "CharField",
                "db_column": "version",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 255},
                "db_field_types": {"": "VARCHAR(255)"},
            },
            {
                "name": "app",
                "field_type": "CharField",
                "db_column": "app",
                "python_type": "str",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {"max_length": 20},
                "db_field_types": {"": "VARCHAR(20)"},
            },
            {
                "name": "content",
                "field_type": "JSONField",
                "db_column": "content",
                "python_type": "Union[dict, list]",
                "generated": False,
                "nullable": False,
                "unique": False,
                "indexed": False,
                "default": None,
                "description": None,
                "docstring": None,
                "constraints": {},
                "db_field_types": {"": "TEXT", "postgres": "JSONB"},
            },
        ],
        "fk_fields": [],
        "backward_fk_fields": [],
        "o2o_fields": [],
        "backward_o2o_fields": [],
        "m2m_fields": [],
    },
}


def test_migrate(mocker: MockerFixture, capsys):
    """
    models.py diff with old_models.py
    - change email pk: id -> email_id
    - change product pk field type: IntField -> BigIntField
    - change config pk field attribute: max_length=10 -> max_length=20
    - add field: Email.address
    - add fk field: Config.user
    - drop fk field: Email.user
    - drop field: User.avatar
    - add index: Email.email
    - add unique to indexed field: Email.company
    - change index type for indexed field: Email.slug
    - add many to many: Email.users
    - add one to one: Email.config
    - remove unique: Category.title
    - add unique: User.username
    - change column: length User.password
    - drop unique field: Product.uid
    - add unique_together: (name,type) of Product
    - add one more many to many field: Product.users
    - change unique to normal index: Config.name
    - alter default: Config.status
    - rename column: Product.image -> Product.pic
    - rename column: Product.is_review -> Product.is_reviewed
    - rename column: Product.is_delete -> Product.is_deleted
    - rename fk column: Category.user -> Category.owner
    """
    mocker.patch("asyncclick.prompt", side_effect=(True, True, True, True))

    models_describe = get_models_describe("models")
    Migrate.app = "models"
    if isinstance(Migrate.ddl, SqliteDDL):
        with pytest.raises(NotSupportError):
            Migrate.diff_models(old_models_describe, models_describe)
        Migrate.upgrade_operators.clear()
        with pytest.raises(NotSupportError):
            Migrate.diff_models(models_describe, old_models_describe, False)
        Migrate.downgrade_operators.clear()
    else:
        Migrate.diff_models(old_models_describe, models_describe)
        Migrate.diff_models(models_describe, old_models_describe, False)
        Migrate._merge_operators()
    warning_msg = "Aerich does not handle 'unique' attribution for m2m field. You may need to change the constraints in db manually."
    if isinstance(Migrate.ddl, MysqlDDL):
        expected_upgrade_operators = {
            "ALTER TABLE `category` MODIFY COLUMN `name` VARCHAR(200)",
            "ALTER TABLE `category` MODIFY COLUMN `slug` VARCHAR(100) NOT NULL",
            "ALTER TABLE `category` DROP INDEX `title`",
            "ALTER TABLE `category` RENAME COLUMN `user_id` TO `owner_id`",
            "ALTER TABLE `category` ADD CONSTRAINT `fk_category_user_110d4c63` FOREIGN KEY (`owner_id`) REFERENCES `user` (`id`) ON DELETE CASCADE",
            "ALTER TABLE `category` ADD FULLTEXT INDEX `idx_category_slug_e9bcff` (`slug`)",
            "ALTER TABLE `category` DROP INDEX `idx_category_slug_e9bcff`",
            "ALTER TABLE `email` DROP COLUMN `user_id`",
            "ALTER TABLE `config` DROP INDEX `name`, ADD INDEX `idx_config_name_2c83c8` (`name`)",
            "ALTER TABLE `config` ADD `user_id` INT NOT NULL COMMENT 'User'",
            "ALTER TABLE `config` ADD CONSTRAINT `fk_config_user_17daa970` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE",
            "ALTER TABLE `config` ALTER COLUMN `status` DROP DEFAULT",
            "ALTER TABLE `email` ADD `address` VARCHAR(200) NOT NULL",
            "ALTER TABLE `email` ADD CONSTRAINT `fk_email_config_88e28c1b` FOREIGN KEY (`config_id`) REFERENCES `config` (`slug`) ON DELETE CASCADE",
            "ALTER TABLE `email` ADD `config_id` VARCHAR(20) NOT NULL UNIQUE",
            "ALTER TABLE `email` DROP INDEX `idx_email_company_1c9234`, ADD UNIQUE (`company`)",
            "ALTER TABLE `configs` RENAME TO `config`",
            "ALTER TABLE `product` DROP COLUMN `uuid`",
            "ALTER TABLE `product` DROP INDEX `uuid`",
            "ALTER TABLE `product` RENAME COLUMN `image` TO `pic`",
            "ALTER TABLE `product` ADD `price` DOUBLE",
            "ALTER TABLE `product` ADD `no` CHAR(36) NOT NULL",
            "ALTER TABLE `email` RENAME COLUMN `id` TO `email_id`",
            "ALTER TABLE `product` ADD INDEX `idx_product_name_869427` (`name`, `type_db_alias`)",
            "ALTER TABLE `product` ADD INDEX `idx_product_no_e4d701` (`no`)",
            "ALTER TABLE `email` ADD INDEX `idx_email_email_4a1a33` (`email`)",
            "ALTER TABLE `product` ADD UNIQUE INDEX `uid_product_name_869427` (`name`, `type_db_alias`)",
            "ALTER TABLE `product` ALTER COLUMN `view_num` SET DEFAULT 0",
            "ALTER TABLE `product` RENAME COLUMN `is_delete` TO `is_deleted`",
            "ALTER TABLE `product` RENAME COLUMN `is_review` TO `is_reviewed`",
            "ALTER TABLE `product` MODIFY COLUMN `id` BIGINT NOT NULL",
            "ALTER TABLE `user` DROP COLUMN `avatar`",
            "ALTER TABLE `user` MODIFY COLUMN `password` VARCHAR(100) NOT NULL",
            "ALTER TABLE `user` MODIFY COLUMN `longitude` DECIMAL(10,8) NOT NULL",
            "ALTER TABLE `user` ADD UNIQUE INDEX `username` (`username`)",
            "CREATE TABLE `email_user` (\n    `email_id` INT NOT NULL REFERENCES `email` (`email_id`) ON DELETE CASCADE,\n    `user_id` INT NOT NULL REFERENCES `user` (`id`) ON DELETE CASCADE\n) CHARACTER SET utf8mb4",
            "CREATE TABLE IF NOT EXISTS `newmodel` (\n    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `name` VARCHAR(50) NOT NULL\n) CHARACTER SET utf8mb4",
            "CREATE TABLE `product_user` (\n    `product_id` BIGINT NOT NULL REFERENCES `product` (`id`) ON DELETE CASCADE,\n    `user_id` INT NOT NULL REFERENCES `user` (`id`) ON DELETE CASCADE\n) CHARACTER SET utf8mb4",
            "CREATE TABLE `config_category_map` (\n    `category_id` INT NOT NULL REFERENCES `category` (`id`) ON DELETE CASCADE,\n    `config_id` VARCHAR(20) NOT NULL REFERENCES `config` (`slug`) ON DELETE CASCADE\n) CHARACTER SET utf8mb4",
            "DROP TABLE IF EXISTS `config_category`",
            "ALTER TABLE `config` MODIFY COLUMN `slug` VARCHAR(20) NOT NULL",
        }
        upgrade_operators = set(Migrate.upgrade_operators)
        upgrade_more_than_expected = upgrade_operators - expected_upgrade_operators
        assert not upgrade_more_than_expected
        upgrade_less_than_expected = expected_upgrade_operators - upgrade_operators
        assert not upgrade_less_than_expected

        expected_downgrade_operators = {
            "ALTER TABLE `category` MODIFY COLUMN `name` VARCHAR(200) NOT NULL",
            "ALTER TABLE `category` MODIFY COLUMN `slug` VARCHAR(200) NOT NULL",
            "ALTER TABLE `category` ADD UNIQUE INDEX `title` (`title`)",
            "ALTER TABLE `category` RENAME COLUMN `owner_id` TO `user_id`",
            "ALTER TABLE `category` DROP FOREIGN KEY `fk_category_user_110d4c63`",
            "ALTER TABLE `category` ADD INDEX `idx_category_slug_e9bcff` (`slug`)",
            "ALTER TABLE `category` DROP INDEX `idx_category_slug_e9bcff`",
            "ALTER TABLE `config` DROP INDEX `idx_config_name_2c83c8`, ADD UNIQUE (`name`)",
            "ALTER TABLE `config` DROP FOREIGN KEY `fk_config_user_17daa970`",
            "ALTER TABLE `config` ALTER COLUMN `status` SET DEFAULT 1",
            "ALTER TABLE `config` DROP COLUMN `user_id`",
            "ALTER TABLE `config` MODIFY COLUMN `slug` VARCHAR(10) NOT NULL",
            "ALTER TABLE `config` RENAME TO `configs`",
            "ALTER TABLE `email` ADD `user_id` INT NOT NULL",
            "ALTER TABLE `email` DROP COLUMN `address`",
            "ALTER TABLE `email` DROP COLUMN `config_id`",
            "ALTER TABLE `email` DROP FOREIGN KEY `fk_email_config_88e28c1b`",
            "ALTER TABLE `email` RENAME COLUMN `email_id` TO `id`",
            "ALTER TABLE `email` DROP INDEX `company`, ADD INDEX `idx_email_company_1c9234` (`company`)",
            "ALTER TABLE `email` DROP INDEX `idx_email_email_4a1a33`",
            "ALTER TABLE `product` RENAME COLUMN `pic` TO `image`",
            "ALTER TABLE `product` ADD `uuid` INT NOT NULL UNIQUE",
            "ALTER TABLE `product` DROP INDEX `idx_product_name_869427`",
            "ALTER TABLE `product` DROP COLUMN `price`",
            "ALTER TABLE `product` DROP COLUMN `no`",
            "ALTER TABLE `product` DROP INDEX `uid_product_name_869427`",
            "ALTER TABLE `product` DROP INDEX `idx_product_no_e4d701`",
            "ALTER TABLE `product` ALTER COLUMN `view_num` DROP DEFAULT",
            "ALTER TABLE `product` RENAME COLUMN `is_deleted` TO `is_delete`",
            "ALTER TABLE `product` RENAME COLUMN `is_reviewed` TO `is_review`",
            "ALTER TABLE `product` MODIFY COLUMN `id` INT NOT NULL",
            "ALTER TABLE `user` ADD `avatar` VARCHAR(200) NOT NULL DEFAULT ''",
            "ALTER TABLE `user` DROP INDEX `username`",
            "ALTER TABLE `user` MODIFY COLUMN `password` VARCHAR(200) NOT NULL",
            "DROP TABLE IF EXISTS `email_user`",
            "DROP TABLE IF EXISTS `newmodel`",
            "DROP TABLE IF EXISTS `product_user`",
            "ALTER TABLE `user` MODIFY COLUMN `longitude` DECIMAL(12,9) NOT NULL",
            "CREATE TABLE `config_category` (\n    `config_id` VARCHAR(20) NOT NULL REFERENCES `config` (`slug`) ON DELETE CASCADE,\n    `category_id` INT NOT NULL REFERENCES `category` (`id`) ON DELETE CASCADE\n) CHARACTER SET utf8mb4",
            "DROP TABLE IF EXISTS `config_category_map`",
        }
        downgrade_operators = set(Migrate.downgrade_operators)
        downgrade_more_than_expected = downgrade_operators - expected_downgrade_operators
        assert not downgrade_more_than_expected
        downgrade_less_than_expected = expected_downgrade_operators - downgrade_operators
        assert not downgrade_less_than_expected
        assert warning_msg in capsys.readouterr().out

    elif isinstance(Migrate.ddl, PostgresDDL):
        expected_upgrade_operators = {
            'DROP INDEX IF EXISTS "uid_category_title_f7fc03"',
            'ALTER TABLE "category" ALTER COLUMN "name" DROP NOT NULL',
            'ALTER TABLE "category" ALTER COLUMN "slug" TYPE VARCHAR(100) USING "slug"::VARCHAR(100)',
            'ALTER TABLE "category" RENAME COLUMN "user_id" TO "owner_id"',
            'ALTER TABLE "category" ADD CONSTRAINT "fk_category_user_110d4c63" FOREIGN KEY ("owner_id") REFERENCES "user" ("id") ON DELETE CASCADE',
            'ALTER TABLE "category" DROP CONSTRAINT IF EXISTS "category_title_key"',
            'CREATE INDEX IF NOT EXISTS "idx_category_slug_e9bcff" ON "category" USING HASH ("slug")',
            'DROP INDEX IF EXISTS "idx_category_slug_e9bcff"',
            'ALTER TABLE "configs" RENAME TO "config"',
            'CREATE INDEX IF NOT EXISTS "idx_config_name_2c83c8" ON "config" ("name")',
            'DROP INDEX IF EXISTS "uid_config_name_2c83c8"',
            'ALTER TABLE "config" ADD "user_id" INT NOT NULL',
            'ALTER TABLE "config" ADD CONSTRAINT "fk_config_user_17daa970" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE',
            'ALTER TABLE "config" ALTER COLUMN "status" DROP DEFAULT',
            'ALTER TABLE "config" ALTER COLUMN "slug" TYPE VARCHAR(20) USING "slug"::VARCHAR(20)',
            'ALTER TABLE "email" ADD "config_id" VARCHAR(20) NOT NULL UNIQUE',
            'ALTER TABLE "email" ADD "address" VARCHAR(200) NOT NULL',
            'ALTER TABLE "email" RENAME COLUMN "id" TO "email_id"',
            'ALTER TABLE "email" DROP COLUMN "user_id"',
            'ALTER TABLE "email" ADD CONSTRAINT "fk_email_config_88e28c1b" FOREIGN KEY ("config_id") REFERENCES "config" ("slug") ON DELETE CASCADE',
            'DROP INDEX IF EXISTS "idx_email_company_1c9234"',
            'CREATE UNIQUE INDEX IF NOT EXISTS "uid_email_company_1c9234" ON "email" ("company")',
            'DROP INDEX IF EXISTS "uid_product_uuid_d33c18"',
            'ALTER TABLE "product" DROP COLUMN "uuid"',
            'ALTER TABLE "product" ALTER COLUMN "view_num" SET DEFAULT 0',
            'ALTER TABLE "product" RENAME COLUMN "image" TO "pic"',
            'ALTER TABLE "product" RENAME COLUMN "is_review" TO "is_reviewed"',
            'ALTER TABLE "product" RENAME COLUMN "is_delete" TO "is_deleted"',
            'ALTER TABLE "product" ADD "price" DOUBLE PRECISION',
            'ALTER TABLE "product" ADD "no" UUID NOT NULL',
            'ALTER TABLE "product" ALTER COLUMN "id" TYPE BIGINT USING "id"::BIGINT',
            'ALTER TABLE "user" ALTER COLUMN "password" TYPE VARCHAR(100) USING "password"::VARCHAR(100)',
            'ALTER TABLE "user" DROP COLUMN "avatar"',
            'ALTER TABLE "user" ALTER COLUMN "longitude" TYPE DECIMAL(10,8) USING "longitude"::DECIMAL(10,8)',
            'CREATE INDEX IF NOT EXISTS "idx_product_name_869427" ON "product" ("name", "type_db_alias")',
            'CREATE INDEX IF NOT EXISTS "idx_email_email_4a1a33" ON "email" ("email")',
            'CREATE INDEX IF NOT EXISTS "idx_product_no_e4d701" ON "product" ("no")',
            'CREATE TABLE "email_user" (\n    "email_id" INT NOT NULL REFERENCES "email" ("email_id") ON DELETE CASCADE,\n    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE\n)',
            'CREATE TABLE IF NOT EXISTS "newmodel" (\n    "id" SERIAL NOT NULL PRIMARY KEY,\n    "name" VARCHAR(50) NOT NULL\n)',
            'COMMENT ON COLUMN "config"."user_id" IS \'User\'',
            'CREATE UNIQUE INDEX IF NOT EXISTS "uid_product_name_869427" ON "product" ("name", "type_db_alias")',
            'CREATE UNIQUE INDEX IF NOT EXISTS "uid_user_usernam_9987ab" ON "user" ("username")',
            'CREATE TABLE "product_user" (\n    "product_id" BIGINT NOT NULL REFERENCES "product" ("id") ON DELETE CASCADE,\n    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE\n)',
            'CREATE TABLE "config_category_map" (\n    "category_id" INT NOT NULL REFERENCES "category" ("id") ON DELETE CASCADE,\n    "config_id" VARCHAR(20) NOT NULL REFERENCES "config" ("slug") ON DELETE CASCADE\n)',
            'DROP TABLE IF EXISTS "config_category"',
        }
        upgrade_operators = set(Migrate.upgrade_operators)
        upgrade_more_than_expected = upgrade_operators - expected_upgrade_operators
        assert not upgrade_more_than_expected
        upgrade_less_than_expected = expected_upgrade_operators - upgrade_operators
        assert not upgrade_less_than_expected

        expected_downgrade_operators = {
            'CREATE UNIQUE INDEX IF NOT EXISTS "uid_category_title_f7fc03" ON "category" ("title")',
            'ALTER TABLE "category" ALTER COLUMN "name" SET NOT NULL',
            'ALTER TABLE "category" ALTER COLUMN "slug" TYPE VARCHAR(200) USING "slug"::VARCHAR(200)',
            'ALTER TABLE "category" RENAME COLUMN "owner_id" TO "user_id"',
            'ALTER TABLE "category" DROP CONSTRAINT IF EXISTS "fk_category_user_110d4c63"',
            'DROP INDEX IF EXISTS "idx_category_slug_e9bcff"',
            'CREATE INDEX IF NOT EXISTS "idx_category_slug_e9bcff" ON "category" ("slug")',
            'ALTER TABLE "config" ALTER COLUMN "status" SET DEFAULT 1',
            'ALTER TABLE "config" DROP CONSTRAINT IF EXISTS "fk_config_user_17daa970"',
            'ALTER TABLE "config" DROP COLUMN "user_id"',
            'ALTER TABLE "config" ALTER COLUMN "slug" TYPE VARCHAR(10) USING "slug"::VARCHAR(10)',
            'DROP INDEX IF EXISTS "idx_config_name_2c83c8"',
            'CREATE UNIQUE INDEX IF NOT EXISTS "uid_config_name_2c83c8" ON "config" ("name")',
            'ALTER TABLE "config" RENAME TO "configs"',
            'ALTER TABLE "email" ADD "user_id" INT NOT NULL',
            'ALTER TABLE "email" DROP COLUMN "address"',
            'ALTER TABLE "email" RENAME COLUMN "email_id" TO "id"',
            'ALTER TABLE "email" DROP COLUMN "config_id"',
            'ALTER TABLE "email" DROP CONSTRAINT IF EXISTS "fk_email_config_88e28c1b"',
            'CREATE INDEX IF NOT EXISTS "idx_email_company_1c9234" ON "email" ("company")',
            'DROP INDEX IF EXISTS "uid_email_company_1c9234"',
            'ALTER TABLE "product" ADD "uuid" INT NOT NULL UNIQUE',
            'ALTER TABLE "product" ALTER COLUMN "view_num" DROP DEFAULT',
            'ALTER TABLE "product" RENAME COLUMN "pic" TO "image"',
            'ALTER TABLE "product" RENAME COLUMN "is_deleted" TO "is_delete"',
            'ALTER TABLE "product" RENAME COLUMN "is_reviewed" TO "is_review"',
            'ALTER TABLE "product" DROP COLUMN "price"',
            'ALTER TABLE "product" DROP COLUMN "no"',
            'ALTER TABLE "product" ALTER COLUMN "id" TYPE INT USING "id"::INT',
            'ALTER TABLE "user" ADD "avatar" VARCHAR(200) NOT NULL DEFAULT \'\'',
            'ALTER TABLE "user" ALTER COLUMN "password" TYPE VARCHAR(200) USING "password"::VARCHAR(200)',
            'ALTER TABLE "user" ALTER COLUMN "longitude" TYPE DECIMAL(12,9) USING "longitude"::DECIMAL(12,9)',
            'ALTER TABLE "user" DROP CONSTRAINT IF EXISTS "user_username_key"',
            'DROP TABLE IF EXISTS "product_user"',
            'DROP INDEX IF EXISTS "idx_product_name_869427"',
            'DROP INDEX IF EXISTS "idx_email_email_4a1a33"',
            'DROP INDEX IF EXISTS "uid_user_usernam_9987ab"',
            'DROP INDEX IF EXISTS "uid_product_name_869427"',
            'DROP INDEX IF EXISTS "idx_product_no_e4d701"',
            'DROP TABLE IF EXISTS "email_user"',
            'DROP TABLE IF EXISTS "newmodel"',
            'CREATE TABLE "config_category" (\n    "config_id" VARCHAR(20) NOT NULL REFERENCES "config" ("slug") ON DELETE CASCADE,\n    "category_id" INT NOT NULL REFERENCES "category" ("id") ON DELETE CASCADE\n)',
            'DROP TABLE IF EXISTS "config_category_map"',
        }
        downgrade_operators = set(Migrate.downgrade_operators)
        downgrade_more_than_expected = downgrade_operators - expected_downgrade_operators
        assert not downgrade_more_than_expected
        downgrade_less_than_expected = expected_downgrade_operators - downgrade_operators
        assert not downgrade_less_than_expected
        assert warning_msg in capsys.readouterr().out

    elif isinstance(Migrate.ddl, SqliteDDL):
        assert Migrate.upgrade_operators == []
        assert Migrate.downgrade_operators == []


def test_sort_all_version_files(mocker):
    mocker.patch(
        "os.listdir",
        return_value=[
            "1_datetime_update.py",
            "11_datetime_update.py",
            "10_datetime_update.py",
            "2_datetime_update.py",
        ],
    )

    Migrate.migrate_location = Path(".")

    assert Migrate.get_all_version_files() == [
        "1_datetime_update.py",
        "2_datetime_update.py",
        "10_datetime_update.py",
        "11_datetime_update.py",
    ]


def test_sort_files_containing_non_migrations(mocker):
    mocker.patch(
        "os.listdir",
        return_value=[
            "1_datetime_update.py",
            "11_datetime_update.py",
            "10_datetime_update.pyc",
            "2_datetime_update.py",
            "not_a_migration.py",
            "999.py",
            "123foo_not_a_migration.py",
        ],
    )

    Migrate.migrate_location = Path(".")

    assert Migrate.get_all_version_files() == [
        "1_datetime_update.py",
        "2_datetime_update.py",
        "10_datetime_update.py",
        "11_datetime_update.py",
    ]


@pytest.fixture
def tmp_migrate_dir(tmp_path):
    Migrate.app = "foo"
    Migrate.migrate_location = tmp_path
    with chdir(tmp_path):
        yield


async def test_empty_migration(mocker, tmp_work_dir: Path) -> None:
    mocker.patch("os.listdir", return_value=[])
    Migrate.migrate_location = tmp_work_dir
    Migrate.app = "models_second"
    expected_content = MIGRATE_TEMPLATE.format(
        upgrade_sql="",
        downgrade_sql="",
        models_state=get_formatted_compressed_data(get_models_describe(Migrate.app)),
    )
    migration_file = await Migrate.migrate("update", True, no_input=True)
    assert Path(migration_file).read_text() == expected_content


async def test_remove_conflicts_empty(mocker, tmp_migrate_dir) -> None:
    Migrate.app = "models"
    # empty migration
    expected_content = MIGRATE_TEMPLATE.format(
        upgrade_sql="",
        downgrade_sql="",
        models_state=get_formatted_compressed_data(get_models_describe(Migrate.app)),
    )
    pre_migrate_file = Path("0_datetime_name.py")
    pre_migrate_file.write_text("Invalid migration content")
    mocker.patch("asyncclick.prompt", side_effect=(False,))
    migration_file = await Migrate.migrate("update", empty=True)
    assert pre_migrate_file.exists()
    assert migration_file is None

    mocker.patch("asyncclick.prompt", side_effect=(True,))
    migration_file = await Migrate.migrate("update", empty=True)
    assert not pre_migrate_file.exists()
    assert migration_file and migration_file.startswith("0_")
    assert Path(migration_file).read_text() == expected_content

    await anyio.sleep(1)  # ensure new migration filename to be generated
    new_migration_file = await Migrate.migrate("update", empty=True, no_input=True)
    assert not Path(migration_file).exists()
    assert new_migration_file.startswith("0_")
    assert Path(new_migration_file).read_text() == expected_content


async def test_remove_conflicts(mocker, tmp_migrate_dir) -> None:
    from tests.models import NewModel

    # normal migration
    mocker.patch("aerich.migrate.get_models_describe", return_value={})
    mocker.patch("aerich.utils.get_models_describe", return_value={})
    Migrate._last_version_content = {}
    init_file = Path("0_datetime_init.py")
    init_file.touch()
    pre_migrate_file = Path("1_datetime_name.py")
    pre_migrate_file.write_text("Invalid migration content")
    mocker.patch("asyncclick.prompt", side_effect=(False,))
    migration_file = await Migrate.migrate("update", empty=False)
    assert pre_migrate_file.exists()
    assert migration_file == ""

    models_describe = {"foo.NewModel": get_models_describe("models")["models.NewModel"]}
    last_version = Aerich(app="foo", content="{}", version=init_file.name)
    mocker.patch("asyncclick.prompt", side_effect=(True,))
    mocker.patch("aerich.migrate.get_models_describe", return_value=models_describe)
    mocker.patch("aerich.migrate.Migrate.get_last_version", return_value=last_version)
    mocker.patch("aerich.migrate.Migrate._get_model", return_value=NewModel)
    migration_file = await Migrate.migrate("update", empty=False)
    assert not pre_migrate_file.exists()
    assert migration_file and migration_file.startswith("1_")

    await anyio.sleep(1)  # ensure new migration filename to be generated
    new_migration_file = await Migrate.migrate("update", empty=True, no_input=True)
    assert not Path(migration_file).exists()
    assert new_migration_file and new_migration_file.startswith("1_")


def _test_migrate_upgrade(max_model_num: int = 2, offline=False) -> None:
    run_shell("aerich init -t settings.TORTOISE_ORM", capture_output=False)
    run_shell("aerich init-db", capture_output=False)
    output = run_shell("pytest -s _tests.py::test_1")
    assert "error" not in output.lower()
    for num in range(2, max_model_num + 1):
        shutil.move(f"models_{num}.py", "models.py")
        output = run_shell("aerich migrate" + " --offline" * offline)
        assert "error" not in output.lower()
        output = run_shell("aerich upgrade")
        assert "error" not in output.lower()
        output = run_shell(f"pytest -s _tests.py::test_{num}")
        assert "error" not in output.lower()


@requires_dialect("sqlite")
def test_migrate_with_rescursive_m2m(tmp_work_dir):
    prepare_py_files("m2m_rescursive")
    _test_migrate_upgrade()


@requires_dialect("postgres")
def test_migrate_with_m2m_comment(tmp_work_dir):
    prepare_py_files("m2m_comment")
    with tmp_daily_db():
        _test_migrate_upgrade()


@requires_dialect("postgres", "mysql")
def test_drop_field_unique(tmp_work_dir):
    prepare_py_files("drop_field_unique")
    with tmp_daily_db():
        _test_migrate_upgrade(5)


@requires_dialect("sqlite")
def test_delete_model_with_m2m_field(tmp_work_dir):
    prepare_py_files("delete_model_with_m2m_field")
    _test_migrate_upgrade(3)


@requires_dialect("sqlite")
def test_migrate_custom_index_offline(tmp_work_dir):
    prepare_py_files("custom_index_offline")
    _test_migrate_upgrade(3, offline=True)


@requires_dialect("postgres", "mysql")
def test_table_creations(tmp_work_dir):
    prepare_py_files("table_creations")
    with tmp_daily_db():
        _test_migrate_upgrade()
