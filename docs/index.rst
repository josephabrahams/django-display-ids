django-display-ids
==================

Stripe-style prefixed IDs for Django, like ``inv_2aUyqjCzEIiEcYMKj7TZtw``, on top
of the UUID fields you already have. No new fields and no migrations.

.. code-block:: python

   from django_display_ids import DisplayIDMixin, DisplayIDModel

   class Invoice(DisplayIDModel):
       display_id_prefix = "inv"
       id = models.UUIDField(primary_key=True, default=uuid.uuid7)
       slug = models.SlugField(unique=True)

   invoice.display_id  # "inv_2aUyqjCzEIiEcYMKj7TZtw"

   class InvoiceDetailView(DisplayIDMixin, DetailView):
       model = Invoice

The view now finds the invoice from any of these in the URL:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw``, the display ID
- ``550e8400-e29b-41d4-a716-446655440000``, the UUID, in any case, with or
  without hyphens
- ``march-invoice``, the slug

Every lookup turns into a plain query on the UUID or slug column, so nothing
extra is stored.

Why display IDs?
----------------

A UUID in a URL or a log line doesn't tell you what it points to. A display ID
does: ``inv_`` is an invoice, ``cust_`` is a customer. The 22 characters after
the prefix are the same UUID in base62, so it stays short and URL-safe and
converts back without a database lookup.

Storing display IDs would mean a string column and index for every model. A
native UUID column is smaller and faster to index, especially time-ordered
UUIDv7. So the database keeps the UUID, and display IDs only exist at the
edges: in URLs, API responses and logs.

People reading URLs and support tickets like display IDs and slugs. Other
systems often already store your UUIDs. This library accepts all three and
turns each into the same query, so you don't have to pick one.

What's covered
--------------

- :doc:`usage/models`: the ``display_id`` property, and manager methods for
  looking up one or many objects
- :doc:`usage/views`: a mixin for class-based views, plus URL converters
- :doc:`usage/drf`: a view mixin, serializer fields that show and accept
  display IDs, and drf-spectacular schemas
- :doc:`usage/admin`: search the admin by display ID, UUID or slug
- :doc:`usage/templatetags`: a filter to show any UUID as a display ID

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Usage Guide

   usage/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/index

.. toctree::
   :maxdepth: 2
   :caption: Advanced

   advanced/index
