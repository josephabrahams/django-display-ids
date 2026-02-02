Django Admin
============

Enable searching by display ID in the Django admin.

DisplayIDAdminSearchMixin
-------------------------

.. code-block:: python

   from django.contrib import admin
   from django_display_ids import DisplayIDAdminSearchMixin

   @admin.register(Invoice)
   class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
       list_display = ["id", "display_id", "name", "created"]
       search_fields = ["name"]  # display ID search is automatic

Now you can search by display ID in the admin search box:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)

For raw UUID search, add the UUID field to ``search_fields``:

.. code-block:: python

   search_fields = ["name", "id"]  # "id" enables raw UUID search

How It Works
------------

The mixin intercepts search queries and checks if they look like a display ID
(contain an underscore). If so, it decodes the display ID and filters by the
UUID field. Otherwise, it falls back to the standard ``search_fields`` behavior.

This means your existing text-based searches continue to work alongside
display ID searches.

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
