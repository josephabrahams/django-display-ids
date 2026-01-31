export PYTHONUNBUFFERED = 1

.PHONY: help test lint docs

help:
	@echo "test      Run tests with coverage"
	@echo "lint      Run pre-commit hooks"
	@echo "docs      Start docs server with live reload"

test:
	uv run pytest --color=yes --cov=src/django_display_ids --cov-report=term:skip-covered --cov-fail-under=0 --no-cov-on-fail

lint:
	uv run pre-commit run --all-files

docs:
	uv run sphinx-autobuild docs docs/_build/html
