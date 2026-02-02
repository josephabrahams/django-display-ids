URL Path Converters
===================

Django path converters for validating identifier formats in URL patterns.

.. module:: django_display_ids.converters

DisplayIDConverter
------------------

.. class:: DisplayIDConverter

   Path converter for display IDs.

   Matches the format ``{prefix}_{base62}`` where:

   - ``prefix`` is 1-16 lowercase letters
   - ``base62`` is exactly 22 alphanumeric characters

   **Regex:** ``[a-z]{1,16}_[0-9A-Za-z]{22}``

   **Example matches:**

   - ``inv_2aUyqjCzEIiEcYMKj7TZtw``
   - ``prod_0000000000000000000000``

   **Does not match:**

   - ``INV_2aUyqjCzEIiEcYMKj7TZtw`` (uppercase prefix)
   - ``550e8400-e29b-41d4-a716-446655440000`` (UUID)

DisplayIDOrUUIDConverter
------------------------

.. class:: DisplayIDOrUUIDConverter

   Path converter for display IDs or UUIDs.

   Matches either format:

   - Display ID: ``{prefix}_{base62}``
   - UUID: hyphenated (``550e8400-e29b-41d4-a716-446655440000``)

   Consistent with Django's built-in ``<uuid:id>`` converter, only hyphenated
   UUIDs are accepted.

   **Example matches:**

   - ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
   - ``550e8400-e29b-41d4-a716-446655440000`` (UUID)

DisplayIDOrSlugConverter
------------------------

.. class:: DisplayIDOrSlugConverter

   Path converter for display IDs or slugs.

   Matches either format:

   - Display ID: ``{prefix}_{base62}``
   - Slug: Django's default slug pattern (``[-a-zA-Z0-9_]+``)

   **Example matches:**

   - ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
   - ``my-product-slug`` (slug)
   - ``product_123`` (slug)

DisplayIDOrUUIDOrSlugConverter
------------------------------

.. class:: DisplayIDOrUUIDOrSlugConverter

   Path converter for display IDs, UUIDs, or slugs.

   Matches any of:

   - Display ID: ``{prefix}_{base62}``
   - UUID: hyphenated (``550e8400-e29b-41d4-a716-446655440000``)
   - Slug: Django's default slug pattern (``[-a-zA-Z0-9_]+``)

   This is the most permissive converter, useful when you want to accept
   any identifier format.

   **Example matches:**

   - ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
   - ``550e8400-e29b-41d4-a716-446655440000`` (UUID)
   - ``my-product-slug`` (slug)

Factory Functions
-----------------

For custom slug patterns, use the factory functions:

.. function:: make_display_id_or_slug_converter(slug_regex=None)

   Create a :class:`DisplayIDOrSlugConverter` with a custom slug regex.

   :param slug_regex: Custom slug regex pattern. If ``None``, uses the
       ``DISPLAY_IDS["SLUG_REGEX"]`` setting.
   :returns: A :class:`DisplayIDOrSlugConverter` subclass with the custom regex.

   .. code-block:: python

      from django_display_ids.converters import make_display_id_or_slug_converter

      # Lowercase slugs only
      LowercaseConverter = make_display_id_or_slug_converter(r"[a-z0-9-]+")
      register_converter(LowercaseConverter, "lowercase_id")

.. function:: make_display_id_or_uuid_or_slug_converter(slug_regex=None)

   Create a :class:`DisplayIDOrUUIDOrSlugConverter` with a custom slug regex.

   :param slug_regex: Custom slug regex pattern. If ``None``, uses the
       ``DISPLAY_IDS["SLUG_REGEX"]`` setting.
   :returns: A :class:`DisplayIDOrUUIDOrSlugConverter` subclass with the custom regex.

   .. code-block:: python

      from django_display_ids.converters import make_display_id_or_uuid_or_slug_converter

      # Lowercase slugs only
      Converter = make_display_id_or_uuid_or_slug_converter(r"[a-z0-9-]+")
      register_converter(Converter, "identifier")

Converter Summary
-----------------

.. list-table::
   :widths: 40 15 15 15
   :header-rows: 1

   * - Converter
     - display_id
     - uuid
     - slug
   * - :class:`DisplayIDConverter`
     - ✓
     -
     -
   * - :class:`DisplayIDOrUUIDConverter`
     - ✓
     - ✓
     -
   * - :class:`DisplayIDOrSlugConverter`
     - ✓
     -
     - ✓
   * - :class:`DisplayIDOrUUIDOrSlugConverter`
     - ✓
     - ✓
     - ✓

.. note::

   For standalone UUID matching, use Django's built-in ``<uuid:param>`` converter.

Usage
-----

Register converters in your URL configuration:

.. code-block:: python

   from django.urls import path, register_converter
   from django_display_ids.converters import (
       DisplayIDConverter,
       DisplayIDOrUUIDConverter,
       DisplayIDOrSlugConverter,
       DisplayIDOrUUIDOrSlugConverter,
   )

   register_converter(DisplayIDConverter, "display_id")
   register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")
   register_converter(DisplayIDOrSlugConverter, "display_id_or_slug")
   register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

   urlpatterns = [
       # Display ID only
       path("invoices/<display_id:id>/", InvoiceDetailView.as_view()),

       # Display ID or UUID
       path("items/<display_id_or_uuid:id>/", ItemView.as_view()),

       # Display ID or slug
       path("products/<display_id_or_slug:id>/", ProductView.as_view()),

       # Any identifier format
       path("resources/<identifier:id>/", ResourceView.as_view()),
   ]

Regex Constants
---------------

The following regex constants are available for use in custom converters:

.. data:: DISPLAY_ID_REGEX

   Regex pattern for display IDs: ``[a-z]{1,16}_[0-9A-Za-z]{22}``

.. data:: SLUG_REGEX

   Django's default slug regex pattern: ``[-a-zA-Z0-9_]+``

   This is imported from Django's :class:`~django.urls.converters.SlugConverter`
   and can be overridden via the ``DISPLAY_IDS["SLUG_REGEX"]`` setting.
