Quick Start
===========

1. Add a prefix to your model
-----------------------------

.. code-block:: python

   # models.py
   import uuid

   from django.db import models
   from django_display_ids import DisplayIDManager, DisplayIDModel

   class Invoice(DisplayIDModel):
       display_id_prefix = "inv"

       id = models.UUIDField(primary_key=True, default=uuid.uuid7)
       slug = models.SlugField(unique=True)

       objects = DisplayIDManager()

Instances now have a ``display_id``:

.. code-block:: python

   >>> invoice.id
   UUID('550e8400-e29b-41d4-a716-446655440000')
   >>> invoice.display_id
   'inv_2aUyqjCzEIiEcYMKj7TZtw'

If the UUID isn't the primary key, name its field with ``uuid_field = "uid"``.
See :doc:`usage/models`.

2. Route any identifier to the view
-----------------------------------

.. code-block:: python

   # urls.py
   from django.urls import path, register_converter
   from django_display_ids import DisplayIDOrUUIDOrSlugConverter

   register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

   urlpatterns = [
       path("invoices/<identifier:id>/", InvoiceDetailView.as_view()),
   ]

The converter only lets through values shaped like a display ID, UUID or slug.
``<str:id>`` works too, and :doc:`reference/converters` lists stricter options.

3. Add the mixin to the view
----------------------------

.. code-block:: python

   # views.py
   from django.views.generic import DetailView
   from django_display_ids import DisplayIDMixin

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_url_kwarg = "id"

For Django REST Framework, use the mixin from ``contrib.rest_framework``:

.. code-block:: python

   from django_display_ids.contrib.rest_framework import DisplayIDMixin

   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       queryset = Invoice.objects.all()
       serializer_class = InvoiceSerializer
       lookup_url_kwarg = "id"

``/invoices/inv_2aUyqjCzEIiEcYMKj7TZtw/``,
``/invoices/550e8400-e29b-41d4-a716-446655440000/`` and
``/invoices/march-invoice/`` now all show the same invoice. A display ID with
another model's prefix, or anything that doesn't match, is a 404.

Next steps
----------

- :doc:`usage/models` for the manager's lookup methods
- :doc:`usage/drf` for serializer fields and OpenAPI schemas
- :doc:`usage/admin` to search the admin by display ID
- :doc:`usage/templatetags` to show display IDs for any UUID in templates
