import re
import shutil
import subprocess  # nosec
import sys
from pathlib import Path

from aerich._compat import tomllib
from aerich.version import __version__
from tests._utils import WINDOWS, requires_env, run_shell


def test_python_m_aerich():
    assert __version__ in run_shell("python -m aerich --version")


@requires_env("AERICH_TEST_POETRY_ADD")
def test_poetry_add(tmp_work_dir: Path):
    poetry = "poetry"
    if shutil.which(poetry) is None:
        poetry = "uvx " + poetry
    root_dir = Path(__file__).parent.resolve().parent
    toml_file = root_dir / "pyproject.toml"
    pyproject = tomllib.loads(toml_file.read_text(encoding="utf-8"))
    requires_python = pyproject["project"]["requires-python"]  # e.g.: ">=3.10"
    run_shell(f"{poetry} init --no-interaction --python={requires_python!r}")
    py = "{}.{}".format(*sys.version_info)
    run_shell(f"{poetry} config --local virtualenvs.in-project true")
    run_shell(f"{poetry} env use {py}")
    package = root_dir
    if WINDOWS and package.anchor != tmp_work_dir.anchor:
        # Fix: path is on mount 'D:', start on mount 'C:'
        tmp_package = Path(package.name)
        tmp_package.mkdir()
        shutil.copytree(package / package.name, tmp_package / package.name)
        for name in ("pyproject.toml", "README.md"):
            shutil.copy(package / name, tmp_package)
        package = tmp_package
    r = subprocess.run([*poetry.split(), "add", package], check=False)  # nosec
    assert r.returncode == 0
    out = subprocess.run(
        [*poetry.split(), "run", "pip", "list"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    ).stdout
    assert re.search(rf"{package.name}\s*{__version__}", out)
