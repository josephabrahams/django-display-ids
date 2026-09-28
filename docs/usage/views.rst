Django Views
============

Integrate display ID lookups with Django's class-based views.

DisplayIDMixin
--------------

Add to any view that uses ``get_object()``. When your model extends
``DisplayIDModel``, the prefix is inherited automatically:

.. code-block:: python

   from django.views.generic import DetailView, UpdateView, DeleteView
   from django_display_ids import DisplayIDMixin

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice  # prefix inherited from Invoice.display_id_prefix
       lookup_url_kwarg = "id"

   # Works with any view that uses get_object()
   class InvoiceUpdateView(DisplayIDMixin, UpdateView):
       model = Invoice
       lookup_url_kwarg = "id"

   class InvoiceDeleteView(DisplayIDMixin, DeleteView):
       model = Invoice
       lookup_url_kwarg = "id"

Configuration Attributes
------------------------

``lookup_url_kwarg``
   The URL parameter name to read. Defaults to ``"pk"``.

``lookup_strategies``
   Tuple of strategies to try, in order. Defaults to
   ``("display_id", "uuid", "slug")`` from settings.

``display_id_prefix``
   Expected prefix for display IDs. When ``None`` (the default),
   auto-detected by ``resolve_object`` from the model's
   ``display_id_prefix`` attribute.

``uuid_field``
   The UUID field name on the model. When ``None`` (the default),
   auto-detected by ``resolve_object`` from the model's ``uuid_field``
   attribute, then the ``DISPLAY_IDS["UUID_FIELD"]`` setting, then ``"id"``.

``slug_field``
   The slug field name for slug lookups. When ``None`` (the default),
   auto-detected by ``resolve_object`` from the model's ``slug_field``
   attribute, then the ``DISPLAY_IDS["SLUG_FIELD"]`` setting, then ``"slug"``.

Overriding the Prefix
~~~~~~~~~~~~~~~~~~~~~

You can override the model's prefix on a specific view if needed:

.. code-block:: python

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_url_kwarg = "id"
       display_id_prefix = "custom"  # overrides Invoice.display_id_prefix

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

An unparseable identifier, a wrong prefix, or no match all raise ``Http404``.

As with Django's own ``get_object()``, a slug that matches more than one row
raises ``MultipleObjectsReturned``, and a missing URL parameter raises
``AttributeError``.
