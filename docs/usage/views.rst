Django Views
============

Integrate display ID lookups with Django's class-based views.

DisplayIDObjectMixin
--------------------

Add to any view that uses ``get_object()``:

.. code-block:: python

   from django.views.generic import DetailView, UpdateView, DeleteView
   from django_display_ids import DisplayIDObjectMixin

   class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       lookup_strategies = ("display_id", "uuid", "slug")
       display_id_prefix = "inv"

   # Works with any view that uses get_object()
   class InvoiceUpdateView(DisplayIDObjectMixin, UpdateView):
       model = Invoice
       lookup_param = "id"
       display_id_prefix = "inv"

   class InvoiceDeleteView(DisplayIDObjectMixin, DeleteView):
       model = Invoice
       lookup_param = "id"
       display_id_prefix = "inv"

Configuration Attributes
------------------------

``lookup_param``
   The URL parameter name to read. Defaults to ``"pk"``.

``lookup_strategies``
   Tuple of strategies to try, in order. Defaults to ``("display_id", "uuid")``
   from settings.

``display_id_prefix``
   Expected prefix for display IDs. Falls back to the model's
   ``display_id_prefix`` if using ``DisplayIDMixin``.

``uuid_field``
   The UUID field name on the model. Defaults to ``"id"``.

``slug_field``
   The slug field name for slug lookups. Defaults to ``"slug"``.

Inheriting Prefix from Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your model uses ``DisplayIDMixin``, you can omit ``display_id_prefix``
on the view:

.. code-block:: python

   class Invoice(DisplayIDMixin, models.Model):
       display_id_prefix = "inv"
       # ...

   class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       # display_id_prefix inherited from Invoice

URL Configuration
-----------------

Use a string parameter in your URL pattern:

.. code-block:: python

   urlpatterns = [
       path("invoices/<str:id>/", InvoiceDetailView.as_view()),
       path("invoices/<str:id>/edit/", InvoiceUpdateView.as_view()),
       path("invoices/<str:id>/delete/", InvoiceDeleteView.as_view()),
   ]

URL Path Converters
~~~~~~~~~~~~~~~~~~~

For stricter URL validation, use the provided path converters. These validate
the identifier format at the routing layer, so invalid formats get a 404 before
reaching your view.

.. code-block:: python

   from django.urls import path, register_converter
   from django_display_ids import (
       DisplayIDConverter,
       UUIDConverter,
       DisplayIDOrUUIDConverter,
   )

   # Register converters (typically in urls.py)
   register_converter(DisplayIDConverter, "display_id")
   register_converter(UUIDConverter, "uuid")
   register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")

   urlpatterns = [
       # Only accepts display IDs (e.g., inv_2aUyqjCzEIiEcYMKj7TZtw)
       path("invoices/<display_id:id>/", InvoiceDetailView.as_view()),

       # Only accepts UUIDs (hyphenated or unhyphenated)
       path("internal/<uuid:id>/", InternalDetailView.as_view()),

       # Accepts either format
       path("items/<display_id_or_uuid:id>/", ItemDetailView.as_view()),
   ]

Available Converters
^^^^^^^^^^^^^^^^^^^^

``DisplayIDConverter``
   Matches display IDs: ``{prefix}_{base62}`` where prefix is 1-16 lowercase
   letters and base62 is exactly 22 alphanumeric characters.

``UUIDConverter``
   Matches UUIDs in both hyphenated (``550e8400-e29b-41d4-a716-446655440000``)
   and unhyphenated (``550e8400e29b41d4a716446655440000``) formats. This is
   more permissive than Django's built-in ``uuid`` converter.

``DisplayIDOrUUIDConverter``
   Matches either display IDs or UUIDs.

.. note::

   Path converters validate format only. Prefix validation (ensuring the
   display ID prefix matches the model) still happens in the view mixin.

Error Handling
--------------

When lookup fails, the mixin raises ``Http404``:

- Invalid identifier format → 404
- Wrong prefix → 404
- Object not found → 404

This matches Django's standard behavior for ``get_object_or_404()``.
