checkfiles = aerich/ tests/ conftest.py
black_opts = -l 100 -t py38
py_warn = PYTHONDEVMODE=1
MYSQL_HOST ?= "127.0.0.1"
MYSQL_PORT ?= 3306
MYSQL_PASS ?= "123456"
POSTGRES_HOST ?= "127.0.0.1"
POSTGRES_PORT ?= 5432
POSTGRES_PASS ?= "123456"

up:
	@poetry update

deps:
	@poetry install -E asyncpg -E asyncmy

style: deps
	isort -src $(checkfiles)
	black $(black_opts) $(checkfiles)

check: deps
	black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	flake8 $(checkfiles)
	bandit -x tests -r $(checkfiles)

test: deps
	$(py_warn) TEST_DB=sqlite://:memory: py.test

test_sqlite:
	$(py_warn) TEST_DB=sqlite://:memory: py.test

test_mysql:
	$(py_warn) TEST_DB="mysql://root:$(MYSQL_PASS)@$(MYSQL_HOST):$(MYSQL_PORT)/test_\{\}" pytest -vv -s

test_postgres:
	$(py_warn) TEST_DB="postgres://postgres:$(POSTGRES_PASS)@$(POSTGRES_HOST):$(POSTGRES_PORT)/test_\{\}" pytest -vv -s

testall: deps test_sqlite test_postgres test_mysql

build: deps
	@poetry build

ci: check testall
