Installation
============

.. code-block:: console

   pip install django-display-ids

With Django REST Framework support, or DRF plus drf-spectacular schemas:

.. code-block:: console

   pip install "django-display-ids[drf]"
   pip install "django-display-ids[spectacular]"

Requires Python 3.12+ and Django 4.2+. Only Django is required; DRF is only
imported if you import from ``django_display_ids.contrib.rest_framework``.

To use the ``display_id`` template filter, add the app to ``INSTALLED_APPS``.
Nothing else needs it:

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       "django_display_ids",
   ]
