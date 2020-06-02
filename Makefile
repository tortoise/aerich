checkfiles = aerich/ tests/ conftest.py
black_opts = -l 100 -t py38
py_warn = PYTHONDEVMODE=1
MYSQL_HOST ?= "127.0.0.1"
MYSQL_PORT ?= 3306
POSTGRES_HOST ?= "127.0.0.1"
POSTGRES_PORT ?= 5432

help:
	@echo "Aerich development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up			Updates dev/test dependencies"
	@echo  "    deps		Ensure dev/test dependencies are installed"
	@echo  "    check		Checks that build is sane"
	@echo  "    lint		Reports all linter violations"
	@echo  "    test		Runs all tests"
	@echo  "    style		Auto-formats the code"

up:
	@poetry update

deps:
	@poetry install

style: deps
	isort -rc $(checkfiles)
	black $(black_opts) $(checkfiles)

check: deps
ifneq ($(shell which black),)
	black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
endif
	flake8 $(checkfiles)
	mypy $(checkfiles)
	pylint -d C,W,R $(checkfiles)
	bandit -r $(checkfiles)
	python setup.py check -mrs

test: deps
	$(py_warn) TEST_DB=sqlite://:memory: py.test

test_sqlite:
	$(py_warn) TEST_DB=sqlite://:memory: py.test

test_mysql:
	$(py_warn) TEST_DB="mysql://root:$(MYSQL_PASS)@$(MYSQL_HOST):$(MYSQL_PORT)/test_\{\}" py.test

test_postgres:
	$(py_warn) TEST_DB="postgres://postgres:$(POSTGRES_PASS)@$(POSTGRES_HOST):$(POSTGRES_PORT)/test_\{\}" py.test

testall: deps test_sqlite test_postgres test_mysql

build:
	@poetry build

publish:
	@poetry publish

ci:
	@act -P ubuntu-latest=nektos/act-environments-ubuntu:18.04 -b