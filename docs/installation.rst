Installation
============

Install from PyPI:

.. code-block:: bash

   pip install django-display-ids

No ``INSTALLED_APPS`` entry required — just import and use.

Requirements
------------

- Python 3.12+
- Django 4.2+

Optional Dependencies
---------------------

For Django REST Framework integration:

.. code-block:: bash

   pip install djangorestframework>=3.14

For automatic OpenAPI schema generation with drf-spectacular:

.. code-block:: bash

   pip install drf-spectacular>=0.28

Both are optional and the package gracefully handles their absence.
