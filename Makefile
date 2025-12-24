src_dir = aerich
checkfiles = $(src_dir) tests/ conftest.py
py_warn = PYTHONDEVMODE=1
pytest_opts = --cov=$(src_dir) --cov-append --tb=native -q
MYSQL_HOST ?= "127.0.0.1"
MYSQL_PORT ?= 3306
MYSQL_PASS ?= "123456"
POSTGRES_HOST ?= "127.0.0.1"
POSTGRES_PORT ?= 5432
POSTGRES_PASS ?= 123456

up:
	@uv lock --upgrade

deps:
	@uv sync --all-extras --all-groups --no-extra asyncmy --no-group=vector $(options)

_style:
	@ruff format $(checkfiles)
	@ruff check --fix $(checkfiles)
style: deps _style

_codeqc:
	mypy $(checkfiles)
	bandit -c pyproject.toml -r $(checkfiles)
	twine check dist/*
codeqc: build _codeqc

_check: _build
	@ruff format --check $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	@ruff check $(checkfiles)
	$(MAKE) _codeqc
check: deps _check

_lint: _build _style _codeqc
lint: deps _lint

test: deps
	$(py_warn) pytest $(pytest_opts)

test_sqlite:
	$(py_warn) TEST_DB=sqlite://:memory: pytest $(pytest_opts)

test_mysql:
	$(py_warn) TEST_DB="mysql://root:$(MYSQL_PASS)@$(MYSQL_HOST):$(MYSQL_PORT)/test_\{\}" pytest -vv -s $(pytest_opts)

test_postgres:
	$(py_warn) TEST_DB="postgres://postgres:$(POSTGRES_PASS)@$(POSTGRES_HOST):$(POSTGRES_PORT)/test_\{\}" pytest -vv -s $(pytest_opts)

test_postgres_vector:
	$(py_warn) AERICH_TEST_VECTOR=1 TEST_DB="postgres://postgres:$(POSTGRES_PASS)@$(POSTGRES_HOST):$(POSTGRES_PORT)/test_\{\}" pytest -vv -s tests/test_inspectdb.py::test_inspect_vector $(pytest_opts)

test_psycopg:
	$(py_warn) TEST_DB="psycopg://postgres:$(POSTGRES_PASS)@$(POSTGRES_HOST):$(POSTGRES_PORT)/test_\{\}" pytest -vv -s $(pytest_opts)

_testall: test_sqlite test_postgres test_mysql
testall: deps _testall

report:
	coverage report -m

_build:
	uv build --clear
build: deps _build

ci: build _check _testall
