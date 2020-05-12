checkfiles = alice/ examples/ tests/ conftest.py
black_opts = -l 100 -t py38
py_warn = PYTHONDEVMODE=1

help:
	@echo "Alice development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    test	Runs all tests"
	@echo  "    style       Auto-formats the code"

deps:
	@which pip-sync > /dev/null || pip install -q pip-tools
	@pip-sync tests/requirements.txt

style: deps
	isort -rc $(checkfiles)
	black $(black_opts) $(checkfiles)