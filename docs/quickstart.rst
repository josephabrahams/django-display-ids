Quick Start
===========

Add the mixin to your model
---------------------------

.. code-block:: python

   # models.py
   import uuid
   from django.db import models
   from django_display_ids import DisplayIDModel

   class Invoice(DisplayIDModel, models.Model):
       display_id_prefix = "inv"
       uuid_field = "uuid"
       uuid = models.UUIDField(default=uuid.uuid7, unique=True)
       slug = models.SlugField(unique=True)

This registers the prefix and adds a ``display_id`` property to your model
instances.

.. note::

   ``uuid.uuid7`` requires Python 3.14+. For earlier versions, use
   ``uuid.uuid4``.

Update your URLconf
-------------------

.. code-block:: python

   # urls.py
   from django.urls import path, register_converter
   from django_display_ids import DisplayIDOrUUIDOrSlugConverter

   register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

   urlpatterns = [
       path("invoices/<identifier:id>/", InvoiceDetailView.as_view()),
   ]

.. tip::

   Using ``<str:id>`` also works but accepts any string. Path converters
   validate the format at the routing layer, returning 404 for invalid formats.
   See :doc:`reference/converters` for all available converters.

Add the mixin to your view
---------------------------

.. code-block:: python

   # Django CBV
   from django.views.generic import DetailView
   from django_display_ids import DisplayIDMixin

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_param = "id"

   # Django REST Framework
   from rest_framework.viewsets import ModelViewSet
   from django_display_ids.contrib.rest_framework import DisplayIDMixin

   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       queryset = Invoice.objects.all()
       serializer_class = InvoiceSerializer
       lookup_url_kwarg = "id"

Your views now accept:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``550e8400-e29b-41d4-a716-446655440000`` (UUID)
- ``my-invoice`` (slug)

What's Happening
----------------

1. ``DisplayIDModel`` registers the prefix on the model
2. The path converter validates the identifier format in the URL
3. ``lookup_param`` / ``lookup_url_kwarg`` tells the view mixin which URL parameter to read
4. The view mixin auto-detects ``display_id_prefix`` from the model
5. The default ``lookup_strategies`` tries display IDs, UUIDs, and slugs (in that order)

The mixin decodes the identifier and looks up the object by UUID (or slug).

Next Steps
----------

- :doc:`usage/models` — Add a ``display_id`` property to your models
- :doc:`usage/views` — Learn all view configuration options
- :doc:`usage/drf` — Django REST Framework integration
