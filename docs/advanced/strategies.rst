Lookup Strategies
=================

Strategies determine how identifiers are parsed and resolved to database records.

Available Strategies
--------------------

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Strategy
     - Format
     - Description
   * - ``display_id``
     - ``prefix_base62uuid``
     - Decode display ID and lookup by UUID field
   * - ``uuid``
     - UUID (v4/v7)
     - Parse as UUID and lookup by UUID field
   * - ``slug``
     - any string
     - Lookup by slug field

How Resolution Works
--------------------

Strategies are tried in order. The first strategy that can parse the identifier
performs the database lookup.

.. code-block:: python

   # With strategies=("display_id", "uuid")

   # "inv_2aUy..." -> display_id strategy matches, decodes UUID, queries
   # "550e8400-..." -> display_id fails, uuid strategy matches, queries
   # "my-slug" -> both fail -> InvalidIdentifierError

Default Strategies
------------------

The default order is ``("display_id", "uuid", "slug")``.

All three strategies are included by default. The slug strategy is a catch-all
— any non-empty string is a valid slug — but it's safe to include globally
because models without a slug field automatically skip the slug strategy.

Strategy Requirements
---------------------

display_id Strategy
~~~~~~~~~~~~~~~~~~~

Requires a configured prefix. Without a prefix, the strategy is skipped.

This prevents accidentally matching display IDs from other models. For example,
if you're looking up an ``Invoice`` with prefix ``inv``, a ``User`` display ID
like ``usr_xxx`` won't match — the strategy detects the wrong prefix.

.. code-block:: python

   # With prefix="inv"
   "inv_xxx" -> matches, decodes, queries
   "usr_xxx" -> UnknownPrefixError (prefix mismatch)

uuid Strategy
~~~~~~~~~~~~~

No configuration required. Attempts to parse the value as a standard UUID.

Works with both hyphenated and non-hyphenated formats:

- ``550e8400-e29b-41d4-a716-446655440000``
- ``550e8400e29b41d4a716446655440000``

slug Strategy
~~~~~~~~~~~~~

Matches any non-empty string and looks up by slug field. Because it matches
anything, **always put it last** in the strategy list.

If the model doesn't have the configured slug field, the slug strategy is
automatically skipped. This means you can safely include ``"slug"`` in your
global default strategies without breaking models that don't have a slug field.

Strategy Ordering Best Practices
--------------------------------

1. **Always put** ``display_id`` **first** — it's the most specific and will
   correctly reject display IDs with wrong prefixes.

2. **Put** ``uuid`` **second** — UUIDs have a distinct format that won't
   accidentally match slugs.

3. **Put** ``slug`` **last** — it's a catch-all that matches any string.

Recommended orders:

.. code-block:: python

   # All formats (default)
   lookup_strategies = ("display_id", "uuid", "slug")

   # Display IDs and UUIDs only (no slugs)
   lookup_strategies = ("display_id", "uuid")

   # UUIDs only (no display IDs)
   lookup_strategies = ("uuid",)
