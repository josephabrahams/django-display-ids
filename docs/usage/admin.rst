Django Admin
============

Enable searching by display ID or UUID in the Django admin.

DisplayIDSearchMixin
--------------------

.. code-block:: python

   from django.contrib import admin
   from django_display_ids import DisplayIDSearchMixin

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDSearchMixin, admin.ModelAdmin):
       list_display = ["id", "display_id", "name", "created"]
       search_fields = ["name"]  # display_id/UUID search is automatic

Now you can search by either format in the admin search box:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``550e8400-e29b-41d4-a716-446655440000`` (raw UUID from logs)

How It Works
------------

The mixin intercepts search queries and checks if they look like a display ID
or UUID. If so, it adds a filter for the UUID field. Otherwise, it falls back
to the standard ``search_fields`` behavior.

This means your existing text-based searches continue to work alongside the
new ID-based searches.

Configuration
-------------

The mixin automatically detects the UUID field from your model's ``uuid_field``
attribute (if using ``DisplayIDMixin``), or defaults to ``id``.

Override with:

.. code-block:: python

   class InvoiceAdmin(DisplayIDSearchMixin, admin.ModelAdmin):
       uuid_field = "uid"  # custom UUID field name

Displaying Display IDs
----------------------

If your model uses ``DisplayIDMixin``, you can include ``display_id`` in
``list_display``:

.. code-block:: python

   class Invoice(DisplayIDMixin, models.Model):
       display_id_prefix = "inv"
       # ...

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDSearchMixin, admin.ModelAdmin):
       list_display = ["id", "display_id", "name"]  # display_id is a property
