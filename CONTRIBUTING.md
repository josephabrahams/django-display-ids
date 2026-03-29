# Contributing

## Setup

Clone the repository and install dependencies:

```sh
git clone https://github.com/josephabrahams/django-display-ids.git
cd django-display-ids
uv sync
```

## Running Tests

```sh
make test
```

Or directly:

```sh
uv run pytest
```

Run across Python and Django versions:

```sh
uvx nox
```

## Linting and Formatting

```sh
make lint
```

Install the pre-commit hooks to run automatically on commit:

```sh
uvx pre-commit install
```

## Building Documentation

```sh
make docs
```

Or on a custom port:

```sh
make docs PORT=4321
```

## Nox Sessions

Available nox sessions:

```sh
uvx nox -s lint        # Run ruff linting
uvx nox -s typecheck   # Run mypy type checking
uvx nox                # Run all test matrix combinations
```

List all sessions with `uvx nox -l`.

## Reporting Issues

Please report bugs and feature requests on GitHub:

https://github.com/josephabrahams/django-display-ids/issues
