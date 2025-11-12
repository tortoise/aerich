import re
import shutil
import subprocess  # nosec
import sys
from pathlib import Path

from aerich.version import __version__
from tests._utils import WINDOWS, requires_env, run_shell


def test_python_m_aerich():
    assert __version__ in run_shell("python -m aerich --version")


@requires_env("AERICH_TEST_POETRY_ADD")
def test_poetry_add(tmp_work_dir: Path):
    poetry = "poetry"
    if shutil.which(poetry) is None:
        poetry = "uvx " + poetry
    run_shell(f'{poetry} init --no-interaction --python=">=3.9"')
    py = "{}.{}".format(*sys.version_info)
    run_shell(f"{poetry} config --local virtualenvs.in-project true")
    run_shell(f"{poetry} env use {py}")
    package = Path(__file__).parent.resolve().parent
    if WINDOWS and package.anchor != tmp_work_dir.anchor:
        # Fix: path is on mount 'D:', start on mount 'C:'
        tmp_package = Path(package.name)
        tmp_package.mkdir()
        shutil.copytree(package / package.name, tmp_package / package.name)
        for name in ("pyproject.toml", "README.md"):
            shutil.copy(package / name, tmp_package)
        package = tmp_package
    r = subprocess.run([*poetry.split(), "add", package])  # nosec
    assert r.returncode == 0
    out = subprocess.run(
        [*poetry.split(), "run", "pip", "list"],
        text=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout
    assert re.search(rf"{package.name}\s*{__version__}", out)
