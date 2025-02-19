from aerich.version import __version__
from tests._utils import run_shell


def test_python_m_aerich():
    assert __version__ in run_shell("python -m aerich --version")
