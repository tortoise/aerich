import os
import shutil
from pathlib import Path
from typing import cast

import pytest
from tortoise.indexes import Index

from aerich._compat import tomllib
from aerich.utils import (
    BadOptionUsage,
    ClickException,
    decompress_dict,
    get_dict_diff_by_key,
    get_formatted_compressed_data,
    get_tortoise_config,
    import_py_file,
    load_tortoise_config,
)
from tests._utils import ASSETS, copy_asset, describe_index, requires_dialect, run_shell


def test_import_py_file() -> None:
    m = import_py_file("aerich/utils.py")
    assert getattr(m, "import_py_file", None)


class TestDiffFields:
    def test_the_same_through_order(self) -> None:
        old = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        new = [
            {"name": "members", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert type(get_dict_diff_by_key(old, new)).__name__ == "generator"
        assert len(diffs) == 1
        assert diffs == [("change", [0, "name"], ("users", "members"))]

    def test_same_through_with_different_orders(self) -> None:
        old = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        new = [
            {"name": "admins", "through": "admins_group"},
            {"name": "members", "through": "users_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 1
        assert diffs == [("change", [0, "name"], ("users", "members"))]

    def test_the_same_field_name_order(self) -> None:
        old = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        new = [
            {"name": "users", "through": "user_groups"},
            {"name": "admins", "through": "admin_groups"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 4
        assert diffs == [
            ("remove", "", [(0, {"name": "users", "through": "users_group"})]),
            ("remove", "", [(0, {"name": "admins", "through": "admins_group"})]),
            ("add", "", [(0, {"name": "users", "through": "user_groups"})]),
            ("add", "", [(0, {"name": "admins", "through": "admin_groups"})]),
        ]

    def test_same_field_name_with_different_orders(self) -> None:
        old = [
            {"name": "admins", "through": "admins_group"},
            {"name": "users", "through": "users_group"},
        ]
        new = [
            {"name": "users", "through": "user_groups"},
            {"name": "admins", "through": "admin_groups"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 4
        assert diffs == [
            ("remove", "", [(0, {"name": "admins", "through": "admins_group"})]),
            ("remove", "", [(0, {"name": "users", "through": "users_group"})]),
            ("add", "", [(0, {"name": "users", "through": "user_groups"})]),
            ("add", "", [(0, {"name": "admins", "through": "admin_groups"})]),
        ]

    def test_drop_one(self) -> None:
        old = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        new = [
            {"name": "admins", "through": "admins_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 1
        assert diffs == [("remove", "", [(0, {"name": "users", "through": "users_group"})])]

    def test_add_one(self) -> None:
        old = [
            {"name": "admins", "through": "admins_group"},
        ]
        new = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 1
        assert diffs == [("add", "", [(0, {"name": "users", "through": "users_group"})])]

    def test_drop_some(self) -> None:
        old = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
            {"name": "staffs", "through": "staffs_group"},
        ]
        new = [
            {"name": "admins", "through": "admins_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 2
        assert diffs == [
            ("remove", "", [(0, {"name": "users", "through": "users_group"})]),
            ("remove", "", [(0, {"name": "staffs", "through": "staffs_group"})]),
        ]

    def test_add_some(self) -> None:
        old = [
            {"name": "staffs", "through": "staffs_group"},
        ]
        new = [
            {"name": "users", "through": "users_group"},
            {"name": "admins", "through": "admins_group"},
            {"name": "staffs", "through": "staffs_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 2
        assert diffs == [
            ("add", "", [(0, {"name": "users", "through": "users_group"})]),
            ("add", "", [(0, {"name": "admins", "through": "admins_group"})]),
        ]

    def test_some_through_unchanged(self) -> None:
        old = [
            {"name": "staffs", "through": "staffs_group"},
            {"name": "admins", "through": "admins_group"},
        ]
        new = [
            {"name": "users", "through": "users_group"},
            {"name": "admins_new", "through": "admins_group"},
            {"name": "staffs_new", "through": "staffs_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 3
        assert diffs == [
            ("change", [0, "name"], ("staffs", "staffs_new")),
            ("change", [0, "name"], ("admins", "admins_new")),
            ("add", "", [(0, {"name": "users", "through": "users_group"})]),
        ]

    def test_some_unchanged_without_drop_or_add(self) -> None:
        old = [
            {"name": "staffs", "through": "staffs_group"},
            {"name": "admins", "through": "admins_group"},
            {"name": "users", "through": "users_group"},
        ]
        new = [
            {"name": "users_new", "through": "users_group"},
            {"name": "admins_new", "through": "admins_group"},
            {"name": "staffs_new", "through": "staffs_group"},
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert len(diffs) == 3
        assert diffs == [
            ("change", [0, "name"], ("staffs", "staffs_new")),
            ("change", [0, "name"], ("admins", "admins_new")),
            ("change", [0, "name"], ("users", "users_new")),
        ]

    def test_use_second_key(self) -> None:
        old = [
            {
                "through": "users_users",
                "_generated": False,
                "backward_key": "users_rel_id",
                "field_type": "ManyToManyFieldInstance",
                "forward_key": "users_id",
                "generated": False,
                "model_name": "models.Users",
                "name": "friends",
                "python_type": "models.Users",
                "related_name": "friends_of",
            },
            {
                "through": "users_users",
                "_generated": True,
                "backward_key": "users_id",
                "field_type": "ManyToManyFieldInstance",
                "forward_key": "users_rel_id",
                "generated": False,
                "model_name": "models.Users",
                "name": "friends_of",
                "python_type": "models.Users",
                "related_name": "friends",
            },
        ]
        new = [
            {
                "through": "users_users",
                "_generated": True,
                "backward_key": "users_id",
                "field_type": "ManyToManyFieldInstance",
                "forward_key": "users_rel_id",
                "generated": False,
                "model_name": "models.Users",
                "name": "friends_of",
                "python_type": "models.Users",
                "related_name": "friends",
            },
            {
                "through": "users_users",
                "_generated": False,
                "backward_key": "users_rel_id",
                "field_type": "ManyToManyFieldInstance",
                "forward_key": "users_id",
                "generated": False,
                "model_name": "models.Users",
                "name": "friends",
                "python_type": "models.Users",
                "related_name": "friends_of",
            },
        ]
        diffs = list(get_dict_diff_by_key(old, new))
        assert not diffs


def test_read_config_from_class_var(tmp_work_dir):
    copy_asset("class_var_config")
    output = run_shell("aerich init -t app.core.config.settings.TORTOISE_ORM")
    assert "Success writing aerich config to pyproject.toml" in output
    output = run_shell("aerich init-db")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_init_db")
    assert "error" not in output.lower()
    with open("app/models.py", "a+") as f:
        f.write("    age = fields.IntField(null=True)\n")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_migrate_upgrade")
    assert "error" not in output.lower()


def test_get_tortoise_config():
    tortoise_orm = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "aerich"
    ]["tortoise_orm"]
    backwards_style = get_tortoise_config(None, tortoise_orm)  # type:ignore
    assert get_tortoise_config(tortoise_orm) == backwards_style
    with pytest.raises(TypeError):
        get_tortoise_config(None, tortoise_orm=tortoise_orm)  # type:ignore
    assert get_tortoise_config(ctx=None, tortoise_orm=tortoise_orm) == backwards_style
    assert get_tortoise_config(tortoise_orm=tortoise_orm) == backwards_style


@requires_dialect("sqlite")
def test_load_tortoise_config():
    assert load_tortoise_config() == {
        "apps": {
            "models": {
                "default_connection": "default",
                "models": [
                    "tests.models",
                    "aerich.models",
                ],
            },
            "models_second": {
                "default_connection": "second",
                "models": [
                    "tests.models_second",
                ],
            },
        },
        "connections": {
            "default": {
                "credentials": {
                    "file_path": ":memory:",
                    "journal_mode": "WAL",
                    "journal_size_limit": 16384,
                },
                "engine": "tortoise.backends.sqlite",
            },
            "second": {
                "credentials": {
                    "file_path": ":memory:",
                    "journal_mode": "WAL",
                    "journal_size_limit": 16384,
                },
                "engine": "tortoise.backends.sqlite",
            },
        },
    }


@pytest.fixture
def no_tortoise_env():
    env_name = "TORTOISE_ORM"
    env_value = os.environ.pop(env_name, None)
    try:
        yield
    finally:
        if env_value is not None:
            os.environ[env_name] = env_value


@requires_dialect("sqlite")
def test_load_tortoise_config_errors(tmp_work_dir, no_tortoise_env):
    with pytest.raises(ClickException, match="Failed to load tortoise config"):
        load_tortoise_config()
    settings_py = ASSETS / "settings.py"
    shutil.copy(settings_py, ".")
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert "error" not in output.lower()
    shutil.move(settings_py.name, settings_py.stem)
    msg = "Error while importing configuration module: No module named 'settings'"
    with pytest.raises(ClickException, match=msg):
        load_tortoise_config()
    Path(settings_py.name).touch()
    with pytest.raises(BadOptionUsage, match='Can\'t get "TORTOISE_ORM" from module'):
        load_tortoise_config()


@requires_dialect("sqlite")
def test_load_tortoise_config_with_kwargs(tmp_work_dir):
    TORTOISE_ORM = {
        "connections": {"default": "sqlite://db.sqlite3"},
        "apps": {"models": {"models": ["models", "aerich.models"]}},
    }
    settings = "settings_v2"  # Should use another file name to avoid loading cached module
    shutil.copy(ASSETS / "settings.py", settings + ".py")
    run_shell(f"aerich init -t {settings}.TORTOISE_ORM")
    assert load_tortoise_config(config_file=Path("pyproject.toml")) == TORTOISE_ORM
    custom_config_file = "aerich.toml"
    shutil.move("pyproject.toml", custom_config_file)
    assert load_tortoise_config(config_file=custom_config_file) == TORTOISE_ORM
    custom_env_name = "TORTOISE_ORM_CONF"
    os.environ[custom_env_name] = f"{settings}.TORTOISE_ORM"
    assert load_tortoise_config(env_name=custom_env_name) == TORTOISE_ORM


def test_model_state_compress_decompress():
    describe = {
        "models.Foo": {
            "name": "models.Foo",
            "app": "models",
            "table": "foo",
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
                "constraints": {"ge": -2147483648, "le": 2147483647},
                "db_field_types": {"": "INT"},
            },
            "data_fields": [],
            "fk_fields": [],
            "backward_fk_fields": [],
            "o2o_fields": [],
            "backward_o2o_fields": [],
            "m2m_fields": [],
            "managed": None,
        }
    }
    field = {
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
        "constraints": {"max_length": 50},
        "db_field_types": {"": "VARCHAR(50)"},
    }
    field_name = cast(str, field["name"])
    index = describe_index(Index(fields=(field_name,)))
    s = get_formatted_compressed_data(describe)
    if isinstance(index, Index):  # tortoise-orm<0.24
        pass
        assert (
            s
            == """
    "eJyNkMFOwzAQRH+lyhmQKBGt+IBKXHrihlC0sTepFWdt7LWgqvLv2E6bhFZI3Oy3Y+/MnI"
    "reSNT+YWdM8bI6FQQ9xsMS360KsHaGCTDUOuuas6D27EBwRA1ojxFJ9MIpy8pQpBS0TtCI"
    "KFTUziiQ+gxYsWmRD+ji4P0jYkUSv9FfrrarGoVa/jKpZNqdecVHm9kr8S4L07a6EkaHnm"
    "axPfLB0KRWxIm2SOiAMX3PLiT7yd055CXR6HSWjBYXbyQ2EDQv4v6zA2Eo9Rfd+BywTVvu"
    "14/lptw+PZfbKMlOJrIZxnhz9vFhbmD/Vgx5DgyjYqqx6a5ADaL7Aierm4lZm7+0t6N+3V"
    "8TIGhzOSnjMPwADdrEgA=="
    """.strip()
        )
    else:
        assert (
            s
            == """
    "eJyNkMFOwzAQRH+lyhmQKBGt+IBKXHrihlC0sTepFWdt7LWgqvLv2E6bhFZI3Oy3Y+/MnI"
    "reSNT+YWdM8bI6FQQ9xsMS360KsHaGCTDUOuuas6D27EBwRA1ojxFJ9MIpy8pQpBS0TtCI"
    "KFTUziiQ+gxYsWmRD+ji4P0jYkUSv9FfrrarGoVa/jKpZNqdecVHm9kr8S4L07a6EkaHnm"
    "axPfLB0KRWxIm2SOiAMX3PLiT7yd055CXR6HSWjBYXbyQ2EDQv4v6zA2Eo9Rfd+BywTVvu"
    "14/lptw+PZfbKMlOJrIZxnhz9vFhbmD/Vgx5DgyjYqqx6a5ADaL7Aierm4lZm7+0t6N+3V"
    "8TIGhzOSnjMPwADdrEgA=="
    """.strip()
        )
    assert decompress_dict(s) == describe
    model_desc = cast(dict[str, list], describe["models.Foo"])
    model_desc["data_fields"].append(field)
    model_desc["indexes"].append(index)
    s = get_formatted_compressed_data(describe)
    if isinstance(index, Index):  # tortoise-orm<0.24
        assert isinstance(s, str)
        assert all(len(i.strip().strip('"')) <= 70 for i in s.splitlines())
        assert (
            s
            == """
    "eJytkl1vmzAUhv9KxdUmdVNGk7XaHUUNST8lGkiWakLGmI/l2GZgQpuI/z7bhJEma7WLcY"
    "Ufv8bnPIetQXlEoPw85tz4drI1GKJEvuzj0xMD5XkPFRAoBJ2Ld4GwFAXCQqIYQUkkikiJ"
    "iywXGWeSsgpAQY5lMGNJjyqW/apIIHhCREoKufH0Q+KMReSZlGq5NcRLrm/TUN23RqDWif"
    "Xoz2tr99h3VxN3jZm7Rot7uKVQLR1/uFw8eD8t/zqkLpDrxxnY9BImpnczrZ0lBQgddwNj"
    "U2bcTTjxGTjO3aUzSsP53Jvx+na5SGtM/Q02YR2yB+/mez2WbICpI8/YXjSfVkajSs5XQZ"
    "wRiF6JzCJVr+ZB18aUibEOKiNhgDlUlPXh/EWknAV900LRhDBSIEHU50VRKcXK4G4QnfXW"
    "Zh9pNe6diUiMKhB7I/nHOWHO1IxlNaVuMFG3fDK/DM+HF2dfhxcyoiv5Q86btr2+9/agNn"
    "A/Mxq9jwRqE7tRd95KqJJjc3aKir+r6/IH8mTJh/I6Ve/Z60Cvr/+t/5M/ip4DICwRqVyO"
    "Bu/I8i3Xnljuh9Hgo5Sm/rR4tedMgRDhVY2KKDja4SZ/K3u8RU16SBBDiRag2mia3ySpWd"
    "s="
        """.strip()
        )
    else:
        assert (
            s
            == """
    "eJytkjFPwzAQhf9K5QkkQKW0tGKrKlWwMFSIBaHISS6JVccOtiNaVfnv3DlNHVqoGNjsd+"
    "8u7z5nx0qdgrQ3S63Zw2DHFC8BD335asB4VQWRBMdj6X3Z3hBbZ3jiUMq4tIBSCjYxonJC"
    "K1RVLSWJOkGjUHmQaiU+aoiczsEVYLDw9o6yUClswNJ1xzIBMvVnZmWdMzLApjJgLY63Xc"
    "8+/H6w21Y+IvNmjOcvDRmrdeRHfltZpOT0etT1Pim39EbKHkeJlnWpgrnaukKrg1soR2oO"
    "Cgx3QOOdqQkGRdoj6/i0ewdLu3CvJ4WM19L14P2RaIJIcF1MY/2COX3lenQ7no5nd/fjGV"
    "p8koMybdr1wu5toyfw/MIaX+eOR+EhAjf/IifkFgU3P6Pr/EfwMPIxvA7VOXqdEPCFH/Cf"
    "+JV8E0lQuSvwOhmegfU6Xy0e56uLyfASodGflq17zEiIebL+5CaNTip6pH/znpbKUXmscM"
    "VzD4DWaJovHjE6og=="
        """.strip()
        )
    assert decompress_dict(s) == describe
