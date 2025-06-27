from __future__ import annotations

import shutil
from pathlib import Path

from tests._utils import run_shell, skip_dialect


def _update_model(from_file: str) -> None:
    abspath = Path(__file__).parent / "assets" / "remove_constraint" / from_file
    shutil.copy(abspath, "models.py")


# TODO: remove skip decorator to test sqlite if alter-column supported
@skip_dialect("sqlite")
def test_remove_unique_constraint(tmp_aerich_project):
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
