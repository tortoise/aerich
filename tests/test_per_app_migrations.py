import shutil
from pathlib import Path

from tests._utils import ASSETS, copy_asset, requires_dialect, run_shell


@requires_dialect("sqlite")
def test_single_app(tmp_work_dir):
    shutil.copy(ASSETS / "settings.py", ".")
    run_shell("aerich init -t settings.TORTOISE_ORM --location './{app}/migrations'")
    models_dir = Path("models")
    models_dir.exists() or models_dir.mkdir()
    models_py = models_dir.joinpath("__init__.py")
    models_py.write_text("""from tortoise import Model, fields
class Foo(Model):
    name = fields.CharField(20)""")
    run_shell("aerich init-db")
    assert not Path("migrations").exists()
    migrations_dir = Path("models/migrations/")
    assert migrations_dir.exists(), list(models_dir.glob("*")) + list(Path().glob("*"))
    assert list(migrations_dir.glob("0_*.py"))
    with models_py.open("a") as f:
        f.write("\n    age = fields.IntField()")
    run_shell("aerich migrate")
    assert list(migrations_dir.glob("1_*.py"))
    out = run_shell("aerich upgrade")
    assert "success" in out.lower()


@requires_dialect("sqlite")
def test_multi_apps(tmp_work_dir):
    copy_asset("per_app_migrations")
    toml_file = Path("pyproject.toml")
    text = toml_file.read_text(encoding="utf-8")
    run_shell("aerich init -t settings.TORTOISE_ORM --location './{app}/migrations'")
    assert not Path("migrations").exists()
    assert Path("auth/migrations").exists(), list(Path().glob("*")) + list(Path("auth").glob("*"))
    assert Path("polls/migrations").exists(), list(Path().glob("*")) + list(Path("polls").glob("*"))
    assert text == toml_file.read_text(encoding="utf-8")

    output = run_shell("aerich --app auth init-db")
    assert "error" not in output.lower()
    assert list(Path("auth/migrations/").glob("0_*.py")), list(Path("auth/migrations").glob("*"))
    output = run_shell("aerich --app polls init-db")
    assert "error" not in output.lower()
    assert list(Path("polls/migrations/").glob("0_*.py")), list(Path("polls/migrations").glob("*"))
    output = run_shell("pytest -s _tests.py::test_1")

    assert "error" not in output.lower()
    shutil.move("models_2.py", "auth/models.py")
    output = run_shell("aerich --app auth migrate")
    assert "error" not in output.lower()
    output = run_shell("aerich --app auth upgrade")
    assert "error" not in output.lower()
    output = run_shell("pytest -s _tests.py::test_2")
    assert "error" not in output.lower()

    shutil.move("models_3.py", "polls/models.py")
    output = run_shell("aerich --app polls migrate")
    assert "error" not in output.lower()
    output = run_shell("aerich --app polls upgrade")
    assert "error" not in output.lower()
    output = run_shell("pytest -s _tests.py::test_3")
    assert "error" not in output.lower()
