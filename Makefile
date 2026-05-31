JUST_INSTALL_HINT = The 'just' command is required. Install it with: uv tool install rust-just
.DEFAULT_GOAL := up

MYSQL_HOST ?= 127.0.0.1
MYSQL_PORT ?= 3306
MYSQL_PASS ?= 123456
POSTGRES_HOST ?= 127.0.0.1
POSTGRES_PORT ?= 5432
POSTGRES_PASS ?= 123456

.PHONY: ensure-just up deps _style style _codeqc codeqc _check check _lint lint test test_sqlite test_mysql test_postgres test_postgres_vector test_psycopg _testall testall report _build build ci

ensure-just:
	@command -v just >/dev/null 2>&1 || (echo "$(JUST_INSTALL_HINT)" >&2; exit 1)

up: ensure-just
	@just up

deps: ensure-just
	@just deps "$(options)"

_style: ensure-just
	@just _style

style: ensure-just
	@just style

_codeqc: ensure-just
	@just _codeqc

codeqc: ensure-just
	@just codeqc

_check: ensure-just
	@just _check

check: ensure-just
	@just check

_lint: ensure-just
	@just _lint

lint: ensure-just
	@just lint

test: ensure-just
	@just test

test_sqlite: ensure-just
	@just test_sqlite

test_mysql: ensure-just
	@MYSQL_HOST="$(MYSQL_HOST)" MYSQL_PORT="$(MYSQL_PORT)" MYSQL_PASS="$(MYSQL_PASS)" just test_mysql

test_postgres: ensure-just
	@POSTGRES_HOST="$(POSTGRES_HOST)" POSTGRES_PORT="$(POSTGRES_PORT)" POSTGRES_PASS="$(POSTGRES_PASS)" just test_postgres

test_postgres_vector: ensure-just
	@POSTGRES_HOST="$(POSTGRES_HOST)" POSTGRES_PORT="$(POSTGRES_PORT)" POSTGRES_PASS="$(POSTGRES_PASS)" just test_postgres_vector

test_psycopg: ensure-just
	@POSTGRES_HOST="$(POSTGRES_HOST)" POSTGRES_PORT="$(POSTGRES_PORT)" POSTGRES_PASS="$(POSTGRES_PASS)" just test_psycopg

_testall: ensure-just
	@just _testall

testall: ensure-just
	@just testall

report: ensure-just
	@just report

_build: ensure-just
	@just _build

build: ensure-just
	@just build

ci: ensure-just
	@just ci
