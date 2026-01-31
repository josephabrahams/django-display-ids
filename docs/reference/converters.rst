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

UUIDConverter
-------------

.. class:: UUIDConverter

   Path converter for UUIDs.

   Matches UUIDs in both hyphenated and unhyphenated formats. This is more
   permissive than Django's built-in ``uuid`` converter, which only accepts
   hyphenated UUIDs.

   **Regex:** ``(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32})``

   **Example matches:**

   - ``550e8400-e29b-41d4-a716-446655440000`` (hyphenated)
   - ``550e8400e29b41d4a716446655440000`` (unhyphenated)

   **Does not match:**

   - ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
   - ``GGGGGGGG-GGGG-GGGG-GGGG-GGGGGGGGGGGG`` (invalid hex)

DisplayIDOrUUIDConverter
------------------------

.. class:: DisplayIDOrUUIDConverter

   Path converter for display IDs or UUIDs.

   Combines the patterns from :class:`DisplayIDConverter` and :class:`UUIDConverter`.

   **Example matches:**

   - ``inv_2aUyqjCzEIiEcYMKj7TZtw`` (display ID)
   - ``550e8400-e29b-41d4-a716-446655440000`` (hyphenated UUID)
   - ``550e8400e29b41d4a716446655440000`` (unhyphenated UUID)

Usage
-----

Register converters in your URL configuration:

.. code-block:: python

   from django.urls import path, register_converter
   from django_display_ids import (
       DisplayIDConverter,
       UUIDConverter,
       DisplayIDOrUUIDConverter,
   )

   register_converter(DisplayIDConverter, "display_id")
   register_converter(UUIDConverter, "uuid")
   register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")

   urlpatterns = [
       path("invoices/<display_id:id>/", InvoiceDetailView.as_view()),
       path("internal/<uuid:id>/", InternalView.as_view()),
       path("items/<display_id_or_uuid:id>/", ItemView.as_view()),
   ]
