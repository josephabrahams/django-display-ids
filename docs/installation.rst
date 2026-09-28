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

   pip install "django-display-ids[drf]"

For OpenAPI schemas with drf-spectacular (includes DRF):

.. code-block:: console

   pip install "django-display-ids[spectacular]"

Only Django is required. DRF is imported only when you import from
``django_display_ids.contrib.rest_framework``.
