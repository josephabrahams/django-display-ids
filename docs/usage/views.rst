Django Views
============

Add ``DisplayIDMixin`` to any class-based view that calls ``get_object()``,
such as ``DetailView``, ``UpdateView`` or ``DeleteView``:

.. code-block:: python

   from django.views.generic import DetailView, UpdateView
   from django_display_ids import DisplayIDMixin

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice
       lookup_url_kwarg = "id"

   class InvoiceUpdateView(DisplayIDMixin, UpdateView):
       model = Invoice
       lookup_url_kwarg = "id"
       fields = ["name"]

``lookup_url_kwarg`` names the URL parameter holding the identifier, and
defaults to ``"pk"``. The mixin takes the prefix, UUID field and slug field
from the model. It searches ``get_queryset()``, so a view that filters its
queryset (for example to the current user's objects) only finds those. Setting
``queryset`` alone, without ``model``, also works.

To change the defaults for one view, set ``display_id_prefix``,
``lookup_strategies``, ``uuid_field`` or ``slug_field`` on it. The same
attributes work on the DRF mixin and the admin mixin. See
:doc:`/reference/settings` for what each one does and its default.

URLs
----

Any URL parameter works, including ``<str:id>``. The converters in this
package only let through values shaped like an identifier:

.. code-block:: python

   from django.urls import path, register_converter
   from django_display_ids import DisplayIDOrUUIDOrSlugConverter

   register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

   urlpatterns = [
       path("invoices/<identifier:id>/", InvoiceDetailView.as_view()),
   ]

A converter only checks the shape. Whether a display ID's prefix belongs to
this model is checked by the mixin. :doc:`/reference/converters` lists all the
converters.

Errors
------

- An identifier that can't be parsed, has another model's prefix, or matches
  nothing raises ``Http404``.
- A slug that matches more than one row raises ``MultipleObjectsReturned``, as
  Django's ``get_object()`` does. Keep slug fields unique.
- A URL without the ``lookup_url_kwarg`` parameter raises ``AttributeError``.
- Lookup settings that can never match, such as ``lookup_strategies =
  ("display_id",)`` on a model without a prefix, raise ``MissingPrefixError``
  or ``ImproperlyConfigured`` instead of a 404.
