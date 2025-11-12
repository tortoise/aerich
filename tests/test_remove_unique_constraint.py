from __future__ import annotations

import functools
import shutil
from pathlib import Path

from tests._utils import prepare_py_files, run_shell, skip_dialect, tmp_daily_db


def update_model(from_file: str, parent: Path) -> None:
    abspath = parent / from_file
    shutil.copy(abspath, "models.py")


# TODO: remove skip decorator to test sqlite if alter-column supported
@skip_dialect("sqlite")
def test_remove_unique_constraint(tmp_work_dir):
    asset_dir = prepare_py_files("remove_constraint")
    with tmp_daily_db():
        _test_remove_unique_constraint(asset_dir)


def _test_remove_unique_constraint(asset_dir: Path) -> None:
    _update_model = functools.partial(update_model, parent=asset_dir)
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert "Success" in output
    output = run_shell("aerich init-db")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_init_db")
    assert "error" not in output.lower()
    _update_model("models_2.py")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_models_2")
    assert "error" not in output.lower()
    _update_model("models_3.py")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_models_3")
    assert "error" not in output.lower()
    _update_model("models_4.py")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_models_4")
    assert "error" not in output.lower()
    _update_model("models_5.py")
    output = run_shell("aerich migrate --no-input")
    assert "Success" in output
    output = run_shell("aerich upgrade")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_models_5")
    assert "error" not in output.lower()
