# Agent Guidelines

## Project

Django library for Stripe-like prefixed display IDs. Published on PyPI as `django-display-ids`.

## Layout

- `src/django_display_ids/`: library source
- `tests/`: pytest test suite (uses Django's SQLite test DB)
- `docs/`: Sphinx docs (reStructuredText)

## Commands

- **Tests**: `python -m pytest tests/ -x -q`
- **Full matrix**: `uvx nox` (Python 3.12–3.14 × Django 4.2–6.1)
- **Lint**: `ruff check .`
- **Format**: `ruff format .`

## Code rules

- Only Django is a required dependency. Nothing outside `src/django_display_ids/contrib/rest_framework/` and `src/django_display_ids/contrib/drf_spectacular/` may import `rest_framework` or `drf_spectacular`.
- Support Python 3.12+ and Django 4.2 through 6.1 (see `noxfile.py`).
- Every lookup path (resolver, managers, admin, view mixins, DRF field) goes through `resolver._Lookup`, so they all accept and reject the same identifiers. Don't add parsing elsewhere.
- Tests must check what their name and docstring say, and must be able to fail (an "override" test that passes the default value proves nothing). Behavior shared by every lookup path is tested once, in `tests/test_consistency.py`.

## Change checklist

When making changes, always update ALL of the following before committing:

1. **Code**: the implementation itself
2. **Tests**: add or update tests covering the change
3. **Docs** (`docs/`): update any relevant `.rst` files (especially usage examples)
4. **Docstrings**: update code examples in docstrings that show the changed patterns
5. **CHANGELOG.md**: add an entry under the new version
6. **`pyproject.toml` version**: bump the version if releasing

Search for related patterns across docs and docstrings before considering a change complete. Use `grep` for old patterns to make sure nothing is missed.

## Writing style

This applies to docs, the README, docstrings, the CHANGELOG and commit messages.

- Write the way a person explains something to a colleague: short, plain sentences. Lead with what the reader needs, usually an example.
- Avoid em dashes. Use a period, a comma or parentheses instead.
- No marketing language ("seamless", "powerful", "best of both worlds", "just works", "zero X").
- Don't bold the start of every bullet. Use a plain list, or a sentence.
- Say each thing once. Link to the reference page instead of repeating a table of options.
- Every code example must run against the current API. Show real output values, not placeholders that look real.

## Publishing

Releases are triggered by pushing a git tag that matches the `pyproject.toml` version. CI verifies the tag matches, builds, and publishes to PyPI via trusted publishing.
