Django Views
============

Integrate display ID lookups with Django's class-based views.

DisplayIDMixin
--------------

Add to any view that uses ``get_object()``:

.. code-block:: python

   from django.views.generic import DetailView, UpdateView, DeleteView
   from django_display_ids import DisplayIDMixin

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       display_id_prefix = "inv"

   # Works with any view that uses get_object()
   class InvoiceUpdateView(DisplayIDMixin, UpdateView):
       model = Invoice
       lookup_param = "id"
       display_id_prefix = "inv"

   class InvoiceDeleteView(DisplayIDMixin, DeleteView):
       model = Invoice
       lookup_param = "id"
       display_id_prefix = "inv"

Configuration Attributes
------------------------

``lookup_param``
   The URL parameter name to read. Defaults to ``"pk"``.

``lookup_strategies``
   Tuple of strategies to try, in order. Defaults to
   ``("display_id", "uuid", "slug")`` from settings.

``display_id_prefix``
   Expected prefix for display IDs. Falls back to the model's
   ``display_id_prefix`` if using ``DisplayIDModel``.

``uuid_field``
   The UUID field name on the model. When ``None`` (the default),
   auto-detected by ``resolve_object`` from the model's ``uuid_field``
   attribute, then the ``DISPLAY_IDS["UUID_FIELD"]`` setting, then ``"id"``.

``slug_field``
   The slug field name for slug lookups. When ``None`` (the default),
   auto-detected by ``resolve_object`` from the model's ``slug_field``
   attribute, then the ``DISPLAY_IDS["SLUG_FIELD"]`` setting, then ``"slug"``.

Inheriting Prefix from Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your model uses ``DisplayIDModel``, you can omit ``display_id_prefix``
on the view:

.. code-block:: python

   class Invoice(DisplayIDModel, models.Model):
       display_id_prefix = "inv"
       # ...

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       # display_id_prefix inherited from Invoice

URL Configuration
-----------------

Use path converters for URL validation. These validate the identifier format
at the routing layer, so invalid formats get a 404 before reaching your view.

.. code-block:: python

   from django.urls import path, register_converter
   from django_display_ids import (
       DisplayIDConverter,
       DisplayIDOrUUIDConverter,
       DisplayIDOrSlugConverter,
       DisplayIDOrUUIDOrSlugConverter,
   )

   # Register converters (typically in urls.py)
   register_converter(DisplayIDConverter, "display_id")
   register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")
   register_converter(DisplayIDOrSlugConverter, "display_id_or_slug")
   register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

   urlpatterns = [
       # Only accepts display IDs (e.g., inv_2aUyqjCzEIiEcYMKj7TZtw)
       path("invoices/<display_id:id>/", InvoiceDetailView.as_view()),

       # Accepts display ID or UUID
       path("items/<display_id_or_uuid:id>/", ItemDetailView.as_view()),

       # Accepts display ID or slug
       path("products/<display_id_or_slug:id>/", ProductDetailView.as_view()),

       # Accepts any format (display ID, UUID, or slug)
       path("resources/<identifier:id>/", ResourceDetailView.as_view()),
   ]

Using ``<str:id>`` also works but accepts any string without validation.

Available Converters
^^^^^^^^^^^^^^^^^^^^

``DisplayIDConverter``
   Matches display IDs only: ``{prefix}_{base62}``

``DisplayIDOrUUIDConverter``
   Matches display IDs or UUIDs

``DisplayIDOrSlugConverter``
   Matches display IDs or slugs

``DisplayIDOrUUIDOrSlugConverter``
   Matches display IDs, UUIDs, or slugs

For standalone UUID matching, use Django's built-in ``<uuid:id>`` converter.

See :doc:`/reference/converters` for full details and custom slug patterns.

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
