Quick Start
===========

This guide shows you how to add display ID support to a Django view in under a minute.

Basic Example
-------------

Add the mixin to any Django class-based view:

.. code-block:: python

   from django.views.generic import DetailView
   from django_display_ids import DisplayIDObjectMixin

   class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       lookup_strategies = ("display_id", "uuid")
       display_id_prefix = "inv"

Configure your URL:

.. code-block:: python

   # urls.py
   urlpatterns = [
       path("invoices/<str:id>/", InvoiceDetailView.as_view()),
   ]

Now your view accepts both formats:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``550e8400-e29b-41d4-a716-446655440000`` (UUID)

What's Happening
----------------

1. The ``lookup_param = "id"`` tells the mixin to read from the ``id`` URL parameter
2. The ``lookup_strategies`` defines which formats to accept (in order)
3. The ``display_id_prefix = "inv"`` validates that display IDs start with ``inv_``

The mixin decodes the display ID to extract the UUID, then looks up the object.

Next Steps
----------

- :doc:`usage/models` — Add a ``display_id`` property to your models
- :doc:`usage/views` — Learn all view configuration options
- :doc:`usage/drf` — Django REST Framework integration
