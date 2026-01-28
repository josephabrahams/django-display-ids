django-display-ids
==================

Stripe-like prefixed IDs for Django. Works with existing UUIDs — no schema changes.

Display IDs are human-friendly identifiers like ``inv_2aUyqjCzEIiEcYMKj7TZtw`` — a short
prefix indicating the object type, followed by a base62-encoded UUID. This format,
popularized by Stripe, makes IDs recognizable at a glance while remaining URL-safe and compact.

This library focuses on **lookup only** — it works with your existing UUID fields and
requires no migrations or schema changes.

Features
--------

- **Multiple identifier formats**: display ID (``prefix_base62uuid``), UUID (v4/v7), slug
- **Framework support**: Django CBVs and Django REST Framework
- **Zero model changes required**: Works with any existing UUID field
- **Stateless**: Pure lookup, no database writes

.. code-block:: python

   from django.views.generic import DetailView
   from django_display_ids import DisplayIDObjectMixin

   class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
       model = Invoice
       lookup_param = "id"
       lookup_strategies = ("display_id", "uuid")
       display_id_prefix = "inv"

Now your view accepts both formats:

- ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
- ``550e8400-e29b-41d4-a716-446655440000`` (UUID)

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

.. toctree::
   :maxdepth: 1
   :caption: Project

   contributing
