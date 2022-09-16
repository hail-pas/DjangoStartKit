checkfiles = core/ apis/ common/ conf/ deploy/ storages/ tasks/ third_apis/
black_opts = -l 120 -t py38
py_warn = PYTHONDEVMODE=1
flake8config = .flake8

help:
	@echo "DjangoStartKit development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up			Updates dependencies"
	@echo  "    deps		Ensure dependencies are installed"
	@echo  "    style		Auto-formats the code"
	@echo  "    check		Checks that build is sane"

up:
	@poetry update

deps:
	@poetry install --no-root

style:
	@poetry run isort --length-sort -src $(checkfiles)
	@poetry run black $(black_opts) $(checkfiles)

check:
	@poetry run black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	@poetry run flake8 --max-line-length=120 --ignore=E131,W503,E203 $(checkfiles) --exclude=*/migrations/*
# poetry run bandit -r $(checkfiles)

