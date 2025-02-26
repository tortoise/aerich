import subprocess  # nosec
from pathlib import Path

from aerich.version import __version__
from tests._utils import chdir, run_shell


def test_python_m_aerich():
    assert __version__ in run_shell("python -m aerich --version")


def test_poetry_add(tmp_path: Path):
    package = Path(__file__).parent.resolve().parent
    with chdir(tmp_path):
        subprocess.run(["poetry", "new", "foo"])  # nosec
        with chdir("foo"):
            r = subprocess.run(["poetry", "add", package])  # nosec
            assert r.returncode == 0
