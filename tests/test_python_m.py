import subprocess  # nosec
from pathlib import Path

from aerich.version import __version__
from tests._utils import run_shell


def test_python_m_aerich():
    assert __version__ in run_shell("python -m aerich --version")


def test_poetry_add(tmp_work_dir: Path):
    run_shell('poetry init --no-interaction --python=">=3.9"')
    package = Path(__file__).parent.resolve().parent
    r = subprocess.run(["poetry", "add", package])  # nosec
    assert r.returncode == 0
