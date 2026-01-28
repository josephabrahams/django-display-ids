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

Build the docs locally:

.. code-block:: bash

   uv pip install -r docs/requirements.txt
   sphinx-build docs docs/_build/html

Preview in your browser:

.. code-block:: bash

   python -m http.server -d docs/_build/html

Reporting Issues
----------------

Please report bugs and feature requests on GitHub:

https://github.com/josephabrahams/django-display-ids/issues
