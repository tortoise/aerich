#!/usr/bin/env -S just --justfile
# ^ A shebang isn't required, but allows a justfile to be executed
#   like a script, with `./justfile lint`, for example.
# Use powershell for Windows so that 'Git Bash' and 'PyCharm Terminal' get the same result

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

src_dir := "aerich"
checkfiles := src_dir + " tests/ conftest.py"
pytest_opts := "--cov=aerich --cov-append --tb=native -q"
test_db := "/test_\\{\\}"
mysql_url := "mysql://root:" + env_var_or_default("MYSQL_PASS", "123456") + "@" + env_var_or_default("MYSQL_HOST", "127.0.0.1") + ":" + env_var_or_default("MYSQL_PORT", "3306") + test_db
postgres_test_uri := env_var_or_default("POSTGRES_USER", "postgres") + ":" + env_var_or_default("POSTGRES_PASS", "123456") + "@" + env_var_or_default("POSTGRES_HOST", "127.0.0.1") + ":" + env_var_or_default("POSTGRES_PORT", "5432") + test_db
postgres_url := "postgres://" + postgres_test_uri
psycopg_url := "psycopg://" + postgres_test_uri

default:
    @just --list

up:
    uv lock --upgrade

deps options="":
    uv sync --all-extras --all-groups --no-extra asyncmy --no-group=vector {{ options }}

_style *args:
    just _ruff format {{ checkfiles }} {{ args }}
    just _ruff check {{ checkfiles }} --fix {{ args }}

[unix]
_ruff command *args:
    uv run --no-sync ruff {{ command }} {{ args }}

[windows]
_ruff command *args:
    uv run --no-sync ruff {{ command }} --force-exclude --exclude tests/assets {{ args }}

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
