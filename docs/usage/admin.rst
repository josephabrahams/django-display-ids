Django Admin
============

Enable searching by display ID or raw UUID in the Django admin.

DisplayIDAdminSearchMixin
-------------------------

.. code-block:: python

   from django.contrib import admin
   from django_display_ids import DisplayIDAdminSearchMixin

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       list_display = ["id", "display_id", "name", "created"]
       search_fields = ["name"]  # display ID and UUID search is automatic

Now you can search by display ID or raw UUID in the admin search box:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``01970b3e-1234-5678-9abc-def012345678`` (UUID with hyphens)
- ``01970b3e123456789abcdef012345678`` (UUID without hyphens)

How It Works
------------

The mixin intercepts search queries and checks if they look like a display ID
(contain an underscore) or a raw UUID. If so, it decodes the display ID or
parses the UUID and does an exact match against the UUID field. Otherwise, it
falls back to the standard ``search_fields`` behavior.

This means your existing text-based searches continue to work alongside
display ID and UUID searches.

Configuration
-------------

The mixin automatically detects the UUID field from your model's ``uuid_field``
attribute (if using ``DisplayIDModel``), or defaults to ``id``.

Override with:

.. code-block:: python

   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       uuid_field = "uid"  # custom UUID field name

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
