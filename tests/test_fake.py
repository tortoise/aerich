from __future__ import annotations

import os
import re
from pathlib import Path

from tests._utils import Dialect, run_shell


def _append_field(*files: str, name="field_1") -> None:
    for file in files:
        p = Path(file)
        field = f"    {name} = fields.IntField(default=0)"
        with p.open("a") as f:
            f.write(os.linesep + field)


def test_fake(new_aerich_project):
    if Dialect.is_sqlite():
        # TODO: go ahead if sqlite alter-column supported
        return
    output = run_shell("aerich init -t settings.TORTOISE_ORM")
    assert "Success" in output
    output = run_shell("aerich init-db")
    assert "Success" in output
    output = run_shell("aerich --app models_second init-db")
    assert "Success" in output
    output = run_shell("pytest _tests.py::test_init_db")
    assert "error" not in output.lower()
    _append_field("models.py", "models_second.py")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich --app models_second migrate")
    assert "Success" in output
    output = run_shell("aerich upgrade --fake")
    assert "FAKED" in output
    output = run_shell("aerich --app models_second upgrade --fake")
    assert "FAKED" in output
    output = run_shell("pytest _tests.py::test_fake_field_1")
    assert "error" not in output.lower()
    _append_field("models.py", "models_second.py", name="field_2")
    output = run_shell("aerich migrate")
    assert "Success" in output
    output = run_shell("aerich --app models_second migrate")
    assert "Success" in output
    output = run_shell("aerich heads")
    assert "_update.py" in output
    output = run_shell("aerich upgrade --fake")
    assert "FAKED" in output
    output = run_shell("aerich --app models_second upgrade --fake")
    assert "FAKED" in output
    output = run_shell("pytest _tests.py::test_fake_field_2")
    assert "error" not in output.lower()
    output = run_shell("aerich heads")
    assert "No available heads." in output
    output = run_shell("aerich --app models_second heads")
    assert "No available heads." in output
    _append_field("models.py", "models_second.py", name="field_3")
    run_shell("aerich migrate", capture_output=False)
    run_shell("aerich --app models_second migrate", capture_output=False)
    run_shell("aerich upgrade --fake", capture_output=False)
    run_shell("aerich --app models_second upgrade --fake", capture_output=False)
    output = run_shell("aerich downgrade --fake -v 2 --yes", input="y\n")
    assert "FAKED" in output
    output = run_shell("aerich --app models_second downgrade --fake -v 2 --yes", input="y\n")
    assert "FAKED" in output
    output = run_shell("aerich heads")
    assert "No available heads." not in output
    assert not re.search(r"1_\d+_update\.py", output)
    assert re.search(r"2_\d+_update\.py", output)
    output = run_shell("aerich --app models_second heads")
    assert "No available heads." not in output
    assert not re.search(r"1_\d+_update\.py", output)
    assert re.search(r"2_\d+_update\.py", output)
    output = run_shell("aerich downgrade --fake -v 1 --yes", input="y\n")
    assert "FAKED" in output
    output = run_shell("aerich --app models_second downgrade --fake -v 1 --yes", input="y\n")
    assert "FAKED" in output
    output = run_shell("aerich heads")
    assert "No available heads." not in output
    assert re.search(r"1_\d+_update\.py", output)
    assert re.search(r"2_\d+_update\.py", output)
    output = run_shell("aerich --app models_second heads")
    assert "No available heads." not in output
    assert re.search(r"1_\d+_update\.py", output)
    assert re.search(r"2_\d+_update\.py", output)
    output = run_shell("aerich upgrade --fake")
    assert "FAKED" in output
    output = run_shell("aerich --app models_second upgrade --fake")
    assert "FAKED" in output
    output = run_shell("aerich heads")
    assert "No available heads." in output
    output = run_shell("aerich --app models_second heads")
    assert "No available heads." in output
    output = run_shell("aerich downgrade --fake -v 1 --yes", input="y\n")
    assert "FAKED" in output
    output = run_shell("aerich --app models_second downgrade --fake -v 1 --yes", input="y\n")
    assert "FAKED" in output
    output = run_shell("aerich heads")
    assert "No available heads." not in output
    assert re.search(r"1_\d+_update\.py", output)
    assert re.search(r"2_\d+_update\.py", output)
    output = run_shell("aerich --app models_second heads")
    assert "No available heads." not in output
    assert re.search(r"1_\d+_update\.py", output)
    assert re.search(r"2_\d+_update\.py", output)
