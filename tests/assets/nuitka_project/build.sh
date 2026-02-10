#!/bin/sh
set -eu

uv run --no-sync --no-python-downloads --active nuitka --standalone \
  --output-dir=dist \
  --output-filename=minirepro \
  --include-package=app \
  --include-package=tortoise.backends.sqlite \
  --include-package=aerich.ddl.sqlite \
  --include-data-files=app/migrations=app/migrations/=**/*.py \
  main.py
