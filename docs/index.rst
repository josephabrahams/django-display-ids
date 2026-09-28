django-display-ids
==================

Stripe-style prefixed IDs for Django, like ``inv_2aUyqjCzEIiEcYMKj7TZtw``, on top
of the UUID fields you already have. No new fields and no migrations.

.. code-block:: python

   from django_display_ids import DisplayIDMixin, DisplayIDModel

   class Invoice(DisplayIDModel):
       display_id_prefix = "inv"
       id = models.UUIDField(primary_key=True, default=uuid.uuid4)
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

People reading URLs and support tickets like display IDs and slugs. Other
systems often already store your UUIDs. This library accepts all three and
turns each into the same query, so you don't have to pick one.

It works with Django's class-based views, Django REST Framework (views,
serializer fields and drf-spectacular schemas), the admin search box and
templates.

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
