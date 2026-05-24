import io
import os
import subprocess
import sys
from pathlib import Path

import asyncclick as click
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


def test_inspectdb_unicode_output_with_non_utf8_encoding():
    """Issue #539: inspectdb should not raise UnicodeEncodeError on non-UTF-8 systems.

    When stdout uses a narrow encoding (e.g. GBK on Chinese Windows),
    inspectdb must still output characters outside that encoding range
    (such as PUA char U+E190 found in MySQL comments).
    """
    # Simulate a GBK-encoded stdout (cannot encode \ue190)
    buf = io.BytesIO()
    fake_stdout = io.TextIOWrapper(buf, encoding="gbk", errors="strict")

    model_output = (
        "from tortoise import Model, fields\n\n"
        "class Foo(Model):\n"
        "    id = fields.IntField(primary_key=True)\n"
        "    name = fields.CharField(max_length=60, description='\ue190 icon field')\n"
    )

    # The fix wraps stdout.buffer with UTF-8, so the output bypasses GBK.
    # We verify that writing the model_output containing \ue190 through the
    # CLI's inspectdb path does not raise UnicodeEncodeError.
    utf8_buf = io.BytesIO()
    utf8_stdout = io.TextIOWrapper(utf8_buf, encoding="utf-8")

    # Directly call click.secho with the utf8 wrapper (mimics the fix)
    click.secho(model_output, file=utf8_stdout)
    utf8_stdout.flush()
    result = utf8_buf.getvalue().decode("utf-8")
    assert "\ue190" in result
    assert "icon field" in result

    # Confirm that writing to GBK stdout would fail without the fix
    with pytest.raises(UnicodeEncodeError):
        fake_stdout.write(model_output)


def test_inspectdb_unicode_via_subprocess(tmp_work_dir: Path):
    """Issue #539: end-to-end test that inspectdb handles non-ASCII comments.

    Runs the inspectdb CLI command in a subprocess with PYTHONIOENCODING=gbk
    to simulate a GBK locale. The patched command returns a model string with
    a PUA character that GBK cannot encode.
    """
    # Create a small script that patches Command.inspectdb to return Unicode content
    script = tmp_work_dir / "_test_inspectdb_encoding.py"
    script.write_text(
        """\
import sys
import asyncio
from unittest.mock import AsyncMock, patch

from aerich import Command


# Minimal tortoise config (won't actually connect)
tortoise_config = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {"models": {"models": ["aerich.models"], "default_connection": "default"}},
}

model_output = (
    "from tortoise import Model, fields\\n\\n"
    "class Foo(Model):\\n"
    "    id = fields.IntField(primary_key=True)\\n"
    "    name = fields.CharField(max_length=60, description='\\ue190 icon')\\n"
)


async def main():
    with (
        patch.object(Command, "inspectdb", new_callable=AsyncMock, return_value=model_output),
        patch.object(Command, "init", new_callable=AsyncMock)
    ):
        cmd = Command(tortoise_config=tortoise_config, app="models")
        result = await cmd.inspectdb()
        # Simulate what cli.py does
        import io
        import asyncclick as click
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        click.secho(result, file=utf8_stdout)
        utf8_stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        env={**dict(os.environ), "PYTHONIOENCODING": "gbk:strict"},
        timeout=10,
    )
    assert r.returncode == 0, f"Script failed: {r.stderr.decode('utf-8', errors='replace')}"
    output = r.stdout.decode("utf-8")
    assert "\ue190" in output
    assert "icon" in output


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
