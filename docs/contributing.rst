Contributing
============

Development setup and contribution guidelines.

Setup
-----

Clone the repository and install dependencies:

.. code-block:: bash

   git clone https://github.com/josephabrahams/django-display-ids.git
   cd django-display-ids
   uv sync

Running Tests
-------------

Run the test suite:

.. code-block:: bash

   uv run pytest

Run with coverage:

.. code-block:: bash

   uv run pytest --cov=src/django_display_ids

Run across Python and Django versions:

.. code-block:: bash

   uvx nox

Nox Sessions
------------

Available nox sessions:

.. code-block:: bash

   uvx nox -s lint        # Run ruff linting
   uvx nox -s typecheck   # Run mypy type checking
   uvx nox                # Run all test matrix combinations

List all sessions with ``uvx nox -l``.

Linting and Formatting
----------------------

The project uses ruff for linting and formatting, managed via pre-commit:

.. code-block:: bash

   uvx pre-commit run --all-files

Install the pre-commit hooks to run automatically on commit:

.. code-block:: bash

   uvx pre-commit install

Building Documentation
----------------------

Install the docs dependencies:

.. code-block:: bash

   uv pip install -r docs/requirements-dev.txt

Run a live-reloading server that rebuilds on changes:

.. code-block:: bash

   sphinx-autobuild docs docs/_build/html

This starts a server at http://127.0.0.1:8000 that automatically rebuilds when you edit any docs.

Alternatively, build the docs once:

.. code-block:: bash

   sphinx-build docs docs/_build/html
   python -m http.server -d docs/_build/html

Reporting Issues
----------------

Please report bugs and feature requests on GitHub:

https://github.com/josephabrahams/django-display-ids/issues
