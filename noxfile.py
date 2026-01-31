"""Nox configuration for testing multiple Python and Django versions."""

import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

PYTHON_VERSIONS = ["3.12", "3.13", "3.14"]
DJANGO_VERSIONS = ["4.2", "5.2", "6.0"]

# Compatibility matrix
# Django 4.2: Python 3.8 - 3.12
# Django 5.2: Python 3.10 - 3.13
# Django 6.0: Python 3.12 - 3.14
COMPATIBLE = {
    ("3.12", "4.2"),
    ("3.12", "5.2"),
    ("3.12", "6.0"),
    ("3.13", "5.2"),
    ("3.13", "6.0"),
    ("3.14", "6.0"),
}


@nox.session(python=PYTHON_VERSIONS)
@nox.parametrize("django", DJANGO_VERSIONS)
def tests(session: nox.Session, django: str) -> None:
    """Run tests for a specific Python and Django version combination."""
    if (session.python, django) not in COMPATIBLE:
        session.skip(f"Django {django} is not compatible with Python {session.python}")

    session.install(f"django~={django}.0")
    session.install("pytest", "pytest-django", "djangorestframework", "shortuuid")
    session.install(".")
    session.run("pytest", *session.posargs)


@nox.session(python="3.12")
def lint(session: nox.Session) -> None:
    """Run linting checks."""
    session.install("ruff")
    session.run("ruff", "check", "src", "tests")


@nox.session(python="3.12")
def typecheck(session: nox.Session) -> None:
    """Run type checking."""
    session.install(
        "mypy", "django-stubs", "djangorestframework-stubs", "drf-spectacular"
    )
    session.install(".")
    session.run("mypy", "src")
