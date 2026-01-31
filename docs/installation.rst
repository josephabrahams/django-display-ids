Installation
============

Install from PyPI:

.. code-block:: console

   pip install django-display-ids

Add to ``INSTALLED_APPS``:

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       "django_display_ids",
   ]

.. note::

   Adding to ``INSTALLED_APPS`` is only required for template tags. All other
   features (view mixins, managers, encoding functions) work without it.

Requirements
------------

- Python 3.12+
- Django 4.2+

Optional Dependencies
---------------------

For Django REST Framework integration:

.. code-block:: console

   pip install djangorestframework>=3.14

For automatic OpenAPI schema generation with drf-spectacular:

.. code-block:: console

   pip install drf-spectacular>=0.28

Both are optional and the package gracefully handles their absence.
