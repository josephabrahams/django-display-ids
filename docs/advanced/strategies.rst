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

The default order is ``("display_id", "uuid")``.

The slug strategy is excluded by default because it's a catch-all — any
non-empty string is a valid slug. Include it explicitly when needed:

.. code-block:: python

   lookup_strategies = ("display_id", "uuid", "slug")

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

Requires a slug field on the model. Matches any non-empty string.

Because it matches anything, **always put it last** in the strategy list.

Strategy Ordering Best Practices
--------------------------------

1. **Always put** ``display_id`` **first** — it's the most specific and will
   correctly reject display IDs with wrong prefixes.

2. **Put** ``uuid`` **second** — UUIDs have a distinct format that won't
   accidentally match slugs.

3. **Put** ``slug`` **last** — it's a catch-all that matches any string.

Recommended orders:

.. code-block:: python

   # Display IDs and UUIDs only (most common)
   lookup_strategies = ("display_id", "uuid")

   # All formats including slugs
   lookup_strategies = ("display_id", "uuid", "slug")

   # UUIDs only (no display IDs)
   lookup_strategies = ("uuid",)
