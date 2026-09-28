Django Admin
============

Add ``DisplayIDAdminSearchMixin`` to a ``ModelAdmin`` to search by display ID,
UUID or slug:

.. code-block:: python

   from django.contrib import admin
   from django_display_ids import DisplayIDAdminSearchMixin

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       list_display = ["display_id", "name", "created"]
       search_fields = ["name"]

Searching ``inv_2aUyqjCzEIiEcYMKj7TZtw``,
``550e8400-e29b-41d4-a716-446655440000`` or ``march-invoice`` now finds that
invoice, alongside the normal ``search_fields`` results. ``display_id`` works in
``list_display`` because it's a property on the model.

The search term is parsed the same way a URL is in the view mixins:

- A display ID must use the model's prefix. Searching ``cust_...`` in the
  invoice admin won't match an invoice, even if the UUID is the same.
- Slugs match exactly. Add the slug field to ``search_fields`` too if you want
  partial matches.
- Surrounding whitespace is ignored, so an ID pasted from a log still matches.
- The search only adds matches from the queryset the admin passes in, so it
  respects ``get_queryset()`` scoping.

The mixin takes the same ``lookup_strategies``, ``display_id_prefix``,
``uuid_field`` and ``slug_field`` attributes as the view mixins. See
:doc:`/reference/settings`.

Searching related objects
-------------------------

To also find invoices by their customer's display ID, override
``get_search_results`` and use ``_parse_identifier``:

.. code-block:: python

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       search_fields = ["name"]

       def get_search_results(self, request, queryset, search_term):
           original_queryset = queryset
           queryset, use_distinct = super().get_search_results(
               request, queryset, search_term
           )
           if uuid_val := self._parse_identifier(search_term, model=Customer):
               queryset |= original_queryset.filter(customer_id=uuid_val)
           return queryset, use_distinct

``_parse_identifier`` returns the UUID for a display ID or UUID, and ``None``
for anything else. It never raises. With ``model=``, display IDs must use that
model's prefix; without it, any prefix is accepted.
