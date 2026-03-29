# Agent Guidelines

## Project

Django library for Stripe-like prefixed display IDs. Published on PyPI as `django-display-ids`.

## Layout

- `src/django_display_ids/` — library source
- `tests/` — pytest test suite (uses Django's SQLite test DB)
- `docs/` — Sphinx docs (reStructuredText)

## Commands

- **Tests**: `python -m pytest tests/ -x -q`
- **Full matrix**: `uvx nox` (Python 3.12–3.14 × Django 4.2–6.0)
- **Lint**: `ruff check .`
- **Format**: `ruff format .`

## Change checklist

When making changes, always update ALL of the following before committing:

1. **Code** — the implementation itself
2. **Tests** — add or update tests covering the change
3. **Docs** (`docs/`) — update any relevant `.rst` files (especially usage examples)
4. **Docstrings** — update code examples in docstrings that show the changed patterns
5. **CHANGELOG.md** — add an entry under the new version
6. **`pyproject.toml` version** — bump the version if releasing

Search for related patterns across docs and docstrings before considering a change complete. Use `grep` for old patterns to make sure nothing is missed.

## Publishing

Releases are triggered by pushing a git tag that matches the `pyproject.toml` version. CI verifies the tag matches, builds, and publishes to PyPI via trusted publishing.
