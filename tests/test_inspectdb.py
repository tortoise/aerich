import os
import sys
from pathlib import Path

from tortoise.contrib import test

from tests._utils import (
    Dialect,
    prepare_py_files,
    requires_dialect,
    run_in_subprocess,
    skip_dialect,
    tmp_daily_db,
)


# TODO: remove skip decorator to test sqlite after #384 fixed
@skip_dialect("sqlite")
def test_inspect(new_aerich_project):
    ok, out = run_in_subprocess("aerich init -t settings.TORTOISE_ORM")
    if not ok:
        print("Failed to init:", out)
    ok, out = run_in_subprocess("aerich init-db")
    if not ok:
        print("ERROR init-db:", out)
    ok, ret = run_in_subprocess("aerich inspectdb -t product")
    assert ok, ret
    assert ret.startswith("from tortoise import Model, fields")
    assert "primary_key=True" in ret
    assert "fields.DatetimeField" in ret
    assert "fields.FloatField" in ret
    assert "fields.UUIDField" in ret
    if Dialect.is_mysql():
        assert "db_index=True" in ret


@requires_dialect("postgres")
@test.skipIf(sys.version_info < (3, 11), "tortoise-vector requires python>=3.11")
@test.skipIf(
    not (_v := os.getenv("AERICH_TEST_VECTOR")) or _v.lower() not in ("1", "on", "yes", "true"),
    "Skip as os env 'AERICH_TEST_VECTOR' is not true",
)
def test_inspect_vector(tmp_work_dir: Path):
    prepare_py_files("postgres_vector", suffix=".*")
    with tmp_daily_db():
        ok, out = run_in_subprocess("aerich init-db --pre='CREATE EXTENSION IF NOT EXISTS vector'")
        if not ok:
            print("ERROR init-db:", out)
        ok, ret = run_in_subprocess("aerich inspectdb -t foo")
    assert ok, ret
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
