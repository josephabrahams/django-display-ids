Django Admin
============

Search the admin by display ID, UUID, or slug.

DisplayIDAdminSearchMixin
-------------------------

.. code-block:: python

   from django.contrib import admin
   from django_display_ids import DisplayIDAdminSearchMixin

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       list_display = ["id", "display_id", "name", "created"]
       search_fields = ["name"]

The admin search box now also accepts:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``01970b3e-1234-5678-9abc-def012345678`` (UUID, with or without hyphens)
- ``march-invoice`` (slug, if the model has a slug field)

How it works
------------

The search term is parsed the same way the view mixins and
``resolve_object()`` parse a URL. It uses the same strategies, prefix check,
and field names. If it parses, an exact match is added to the normal
``search_fields`` results, so text search keeps working.

Some details:

- Display IDs must use the model's prefix. Searching ``cust_...`` in the
  invoice admin won't match an invoice, even if the UUIDs are the same.
- Slugs match exactly. Add the slug field to ``search_fields`` if you also
  want partial matches.
- Surrounding whitespace is ignored, so an ID pasted from a terminal or email
  still matches.

Configuration
-------------

The mixin takes the same attributes as the view mixins, with the same
defaults. ``lookup_strategies`` defaults to the ``DISPLAY_IDS["STRATEGIES"]``
setting. ``display_id_prefix`` defaults to the model's ``display_id_prefix``.
``uuid_field`` and ``slug_field`` default to the model's attribute of the same
name, then the ``DISPLAY_IDS`` setting:

.. code-block:: python

   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       lookup_strategies = ("display_id", "uuid")  # no slug search
       display_id_prefix = "inv"
       uuid_field = "uuid"
       slug_field = "handle"

Searching Related UUID Fields
-----------------------------

To search by a related model's display ID or UUID (e.g., find all sessions
belonging to a user), override ``get_search_results`` and use the
``_parse_identifier`` static method:

.. code-block:: python

   @admin.register(Session)
   class SessionAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       search_fields = ["name"]

       def get_search_results(self, request, queryset, search_term):
           original_queryset = queryset
           queryset, use_distinct = super().get_search_results(
               request, queryset, search_term
           )
           # Search the related user's UUID field too
           if uuid_val := self._parse_identifier(search_term, model=User):
               queryset |= original_queryset.filter(
                   user__uid=uuid_val
               )
           return queryset, use_distinct

Now searching by ``user_2aUyqjCzEIi...`` or a raw UUID will also match
sessions belonging to that user.

``_parse_identifier`` is a static method that strips surrounding whitespace,
tries to decode a display ID first, then falls back to raw UUID parsing. It
returns ``None`` for unparseable input and never raises exceptions. Pass
``model=`` to apply that model's rules: display IDs must use its prefix, and
on a model without a prefix only raw UUIDs match.

Displaying Display IDs
----------------------

If your model uses ``DisplayIDModel``, you can include ``display_id`` in
``list_display``:

.. code-block:: python

   class Invoice(DisplayIDModel, models.Model):
       display_id_prefix = "inv"
       # ...

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       list_display = ["id", "display_id", "name"]  # display_id is a property
