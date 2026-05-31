set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

src_dir := "aerich"
checkfiles := "aerich tests/ conftest.py"
pytest_opts := "--cov=aerich --cov-append --tb=native -q"
mysql_url := "mysql://root:" + env_var_or_default("MYSQL_PASS", "123456") + "@" + env_var_or_default("MYSQL_HOST", "127.0.0.1") + ":" + env_var_or_default("MYSQL_PORT", "3306") + "/test_{}"
postgres_url := "postgres://postgres:" + env_var_or_default("POSTGRES_PASS", "123456") + "@" + env_var_or_default("POSTGRES_HOST", "127.0.0.1") + ":" + env_var_or_default("POSTGRES_PORT", "5432") + "/test_{}"
psycopg_url := "psycopg://postgres:" + env_var_or_default("POSTGRES_PASS", "123456") + "@" + env_var_or_default("POSTGRES_HOST", "127.0.0.1") + ":" + env_var_or_default("POSTGRES_PORT", "5432") + "/test_{}"

default:
    @just --list

up:
    uv lock --upgrade

deps options="":
    uv sync --all-extras --all-groups --no-extra asyncmy --no-group=vector {{ options }}

_style files=(checkfiles) *args:
    just _ruff format {{ files }} {{ args }}
    just _ruff check {{ files }} --fix {{ args }}

[unix]
_ruff command files=(checkfiles) *args:
    uv run --no-sync ruff {{ command }} {{ files }} {{ args }}

[windows]
_ruff command files=(checkfiles) *args:
    uv run --no-sync ruff {{ command }} --force-exclude --exclude tests/assets {{ files }} {{ args }}

style: deps _style

_codeqc:
    uv run --no-sync mypy {{ checkfiles }}
    uv run --no-sync bandit -c pyproject.toml -r {{ checkfiles }}
    uv run --no-sync twine check dist/*

codeqc: build _codeqc

_build:
    uv build --offline

_check: _build
    just _ruff format {{ checkfiles }} --check
    just _ruff check {{ checkfiles }}
    just _codeqc

check: deps _check

_lint: _build _style _codeqc

lint: deps _lint

test: deps
    just _pytest

test_sqlite:
    just _pytest_env TEST_DB "sqlite://:memory:"

test_mysql:
    just _pytest_env TEST_DB "{{ mysql_url }}" -vv -s

test_postgres:
    just _pytest_env TEST_DB "{{ postgres_url }}" -vv -s

test_postgres_vector:
    just _pytest_vector "{{ postgres_url }}" -vv -s tests/test_inspectdb.py::test_inspect_vector

test_psycopg:
    just _pytest_env TEST_DB "{{ psycopg_url }}" -vv -s

_pytest *args:
    uv run --no-sync pytest {{ args }} {{ pytest_opts }}

[unix]
_pytest_env env_name env_value *args:
    {{ env_name }}='{{ env_value }}' uv run --no-sync pytest {{ args }} {{ pytest_opts }}

[windows]
_pytest_env env_name env_value *args:
    $env:{{ env_name }} = '{{ env_value }}'; uv run --no-sync pytest {{ args }} {{ pytest_opts }}

[unix]
_pytest_vector db_url *args:
    AERICH_TEST_VECTOR=1 TEST_DB='{{ db_url }}' uv run --no-sync pytest {{ args }} {{ pytest_opts }}

[windows]
_pytest_vector db_url *args:
    $env:AERICH_TEST_VECTOR = '1'; $env:TEST_DB = '{{ db_url }}'; uv run --no-sync pytest {{ args }} {{ pytest_opts }}

_testall: test_sqlite test_postgres test_mysql

testall: deps _testall

report:
    uv run --no-sync coverage report -m

build: deps
    uv build

ci: build _check _testall
