Quick Start
===========

This guide shows you how to add display ID support to your views.

Django Views
------------

Add the mixin to any Django class-based view:

.. code-block:: python

   from django.views.generic import DetailView
   from django_display_ids import DisplayIDMixin

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       lookup_strategies = ("display_id", "uuid", "slug")
       display_id_prefix = "inv"

Configure your URL:

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

Django REST Framework
---------------------

The DRF mixin works the same way:

.. code-block:: python

   from rest_framework.viewsets import ModelViewSet
   from django_display_ids.contrib.rest_framework import DisplayIDMixin

   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       queryset = Invoice.objects.all()
       serializer_class = InvoiceSerializer
       lookup_url_kwarg = "id"
       lookup_strategies = ("display_id", "uuid", "slug")
       display_id_prefix = "inv"

Now your views accept:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``550e8400-e29b-41d4-a716-446655440000`` (UUID)
- ``my-invoice`` (slug)

What's Happening
----------------

1. ``lookup_param`` / ``lookup_url_kwarg`` tells the mixin which URL parameter to read
2. ``lookup_strategies`` defines which formats to accept, in order
3. ``display_id_prefix`` validates that display IDs start with the expected prefix

The mixin decodes the identifier and looks up the object by UUID (or slug).

Next Steps
----------

- :doc:`usage/models` — Add a ``display_id`` property to your models
- :doc:`usage/views` — Learn all view configuration options
- :doc:`usage/drf` — Django REST Framework integration
