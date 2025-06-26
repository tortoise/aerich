import sys
from pathlib import Path

from tortoise.contrib import test

from tests._utils import (
    Dialect,
    prepare_py_files,
    requires_dialect,
    run_shell,
    skip_dialect,
    tmp_daily_db,
)


# TODO: remove skip decorator to test sqlite after #384 fixed
@skip_dialect("sqlite")
def test_inspect(new_aerich_project):
    run_shell("aerich init -t settings.TORTOISE_ORM")
    run_shell("aerich init-db")
    ret = run_shell("aerich inspectdb -t product")
    assert ret.startswith("from tortoise import Model, fields")
    assert "primary_key=True" in ret
    assert "fields.DatetimeField" in ret
    assert "fields.FloatField" in ret
    assert "fields.UUIDField" in ret
    if Dialect.is_mysql():
        assert "db_index=True" in ret


@requires_dialect("postgres")
@test.skipIf(sys.version_info < (3, 11), "tortoise-vector requires python>=3.11")
def test_inspect_vector(tmp_work_dir: Path):
    prepare_py_files("postgres_vector", suffix=".*")
    with tmp_daily_db():
        run_shell("aerich init-db")
        ret = run_shell("aerich inspectdb -t foo")
    expected = """
from tortoise import Model, fields
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise_vector.field import VectorField

class Foo(Model):
    id = fields.IntField(primary_key=True)
    a = fields.IntField()
    b = TSVectorField()
    c = VectorField()
    """
    assert expected.strip() in ret
