django-display-ids
==================

Stripe-like prefixed IDs for Django. Works with existing UUIDs — no schema changes.

Why?
----

UUIDv7 (native in Python 3.14+) offers excellent database performance with time-ordered
indexing. But they lack context — seeing ``550e8400-e29b-41d4-a716-446655440000`` in a
URL or log doesn't tell you what kind of object it refers to.

Display IDs like ``inv_2aUyqjCzEIiEcYMKj7TZtw`` solve this: the prefix identifies the
object type at a glance, and base62 encoding keeps them compact and URL-safe. This format,
popularized by Stripe, is easy to recognize in URLs, logs, and emails. But storing display
IDs in the database is far less efficient than native UUIDs.

Different consumers have different needs:

- **Humans** prefer slugs (``my-invoice``) or display IDs (``inv_xxx``)
- **APIs and integrations** work well with UUIDs

This library gives you the best of both worlds: accept any format in your URLs and API
endpoints, then translate to an efficient UUID lookup in the database. Store UUIDs,
expose whatever format your users need.

It focuses on **lookup only** — it works with your existing UUID fields and requires
no migrations or schema changes.

Features
--------

- **Multiple identifier formats**: display ID (``prefix_base62uuid``), UUID (v4/v7), slug
- **Framework support**: Django CBVs and Django REST Framework
- **Zero model changes required**: Works with any existing UUID field
- **Stateless**: Pure lookup, no database writes

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
