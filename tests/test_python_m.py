import re
import subprocess  # nosec
import sys
from pathlib import Path

from aerich.version import __version__
from tests._utils import run_shell


def test_python_m_aerich():
    assert __version__ in run_shell("python -m aerich --version")


def test_poetry_add(tmp_work_dir: Path):
    run_shell('poetry init --no-interaction --python=">=3.9"')
    py = "{}.{}".format(*sys.version_info)
    run_shell("poetry config --local virtualenvs.in-project true")
    run_shell(f"poetry env use {py}")
    package = Path(__file__).parent.resolve().parent
    r = subprocess.run(["poetry", "add", package])  # nosec
    assert r.returncode == 0
    out = subprocess.run(
        ["poetry", "run", "pip", "list"],
        text=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout
    assert re.search(rf"{package.name}\s*{__version__}", out)
