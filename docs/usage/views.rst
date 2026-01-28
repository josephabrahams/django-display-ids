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
       lookup_strategies = ("display_id", "uuid")
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

URL Configuration
~~~~~~~~~~~~~~~~~

Use a string parameter in your URL pattern:

.. code-block:: python

   urlpatterns = [
       path("invoices/<str:id>/", InvoiceDetailView.as_view()),
       path("invoices/<str:id>/edit/", InvoiceUpdateView.as_view()),
       path("invoices/<str:id>/delete/", InvoiceDeleteView.as_view()),
   ]

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

Error Handling
--------------

When lookup fails, the mixin raises ``Http404``:

- Invalid identifier format → 404
- Wrong prefix → 404
- Object not found → 404

This matches Django's standard behavior for ``get_object_or_404()``.
