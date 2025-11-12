import sys
from pathlib import Path

import pytest

from tests._utils import (
    Dialect,
    prepare_py_files,
    requires_dialect,
    requires_env,
    run_in_subprocess,
    skip_dialect,
    tmp_daily_db,
)


# TODO: remove skip decorator to test sqlite after #384 fixed
@skip_dialect("sqlite")
def test_inspect(tmp_work_dir):
    prepare_py_files("fake", with_testing_models=True)
    with tmp_daily_db():
        _test_inspect()


def _test_inspect() -> None:
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
@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="tortoise-vector requires python3.10 or higher"
)
@requires_env("AERICH_TEST_VECTOR")
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
