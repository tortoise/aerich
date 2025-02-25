from tests._utils import Dialect, run_shell


def test_inspect(new_aerich_project):
    if Dialect.is_sqlite():
        # TODO: test sqlite after #384 fixed
        return
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
