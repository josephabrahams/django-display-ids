URL Converters
==============

.. module:: django_display_ids.converters

Path converters that only let through values shaped like an identifier, so
anything else is a 404 before your view runs. They don't check that a prefix
belongs to the right model; the view mixin does that.

.. code-block:: python

   from django.urls import path, register_converter
   from django_display_ids import DisplayIDOrUUIDOrSlugConverter

   register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

   urlpatterns = [
       path("invoices/<identifier:id>/", InvoiceDetailView.as_view()),
   ]

.. list-table::
   :header-rows: 1

   * - Converter
     - Display ID
     - UUID
     - Slug
   * - ``DisplayIDConverter``
     - yes
     -
     -
   * - ``DisplayIDOrUUIDConverter``
     - yes
     - yes
     -
   * - ``DisplayIDOrSlugConverter``
     - yes
     -
     - yes
   * - ``DisplayIDOrUUIDOrSlugConverter``
     - yes
     - yes
     - yes

What each part matches:

Display ID
   ``[a-z]{1,16}_[0-9A-Za-z]{22}``, for example ``inv_2aUyqjCzEIiEcYMKj7TZtw``.
   An uppercase prefix doesn't match.

UUID
   With or without hyphens, in either case: ``550e8400-e29b-41d4-a716-446655440000``
   or ``550E8400E29B41D4A716446655440000``. Hyphens in only some places don't
   match. Django's own ``<uuid:>`` converter only accepts lowercase with
   hyphens, but UUIDs pasted from tools like ``uuidgen`` are often uppercase.

Slug
   The ``SLUG_REGEX`` setting, which defaults to Django's slug pattern
   ``[-a-zA-Z0-9_]+``. A UUID also matches this, so with
   ``DisplayIDOrSlugConverter`` the view receives UUIDs as well.

Every converter passes the matched text to the view unchanged. When reversing,
a ``uuid.UUID`` is turned into a string, so
``reverse("invoice", kwargs={"id": invoice.id})`` works with any converter
that accepts UUIDs.

Custom slug patterns
--------------------

``make_display_id_or_slug_converter(slug_regex)`` and
``make_display_id_or_uuid_or_slug_converter(slug_regex)`` return a converter
with a different slug pattern for one route, without changing the setting:

.. code-block:: python

   from django_display_ids.converters import make_display_id_or_slug_converter

   register_converter(make_display_id_or_slug_converter(r"[a-z0-9-]+"), "lower_id")

Called without an argument, they use the ``SLUG_REGEX`` setting.

The patterns are exported as ``DISPLAY_ID_REGEX``, ``UUID_REGEX`` and
``SLUG_REGEX`` (Django's default slug pattern) for building your own
converters.
