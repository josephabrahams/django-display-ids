Lookup Strategies
=================

A strategy is one way of reading an identifier. There are three:

``display_id``
   ``inv_2aUyqjCzEIiEcYMKj7TZtw``. Decoded to a UUID, then looked up in the UUID
   field. The prefix must match the model's, or the lookup fails.

``uuid``
   ``550e8400-e29b-41d4-a716-446655440000``. Any UUID version, in either case,
   but only in this hyphenated form. Looked up in the UUID field.

``slug``
   Any other non-empty string, looked up exactly in the slug field.

Strategies are tried in order, and the first one that can read the value is
used. The default is ``("display_id", "uuid", "slug")``. Keep ``slug`` last:
it accepts any string, so nothing after it would ever be tried. Change the
order or leave strategies out with ``lookup_strategies`` on a view, or the
``STRATEGIES`` setting for the whole project (see :doc:`/reference/settings`):

.. code-block:: python

   lookup_strategies = ("display_id", "uuid")  # no slugs
   lookup_strategies = ("display_id",)  # display IDs only

Surrounding whitespace is stripped before parsing.

Skipped strategies
------------------

``display_id`` is skipped on models without a ``display_id_prefix``, and
``slug`` on models without the slug field. That's why the default strategies
are safe for every model.

It also means a display ID for one model never finds a row in a model without a
prefix, even if the UUIDs happen to match.

Which strategy reads a value is decided by its shape alone. If that lookup
finds nothing, the next strategy isn't tried. So a slug shaped like a UUID or
a display ID can't be looked up as a slug. That's why only the hyphenated UUID
form counts: 32 hex digits without hyphens (an MD5 hash, say), braces and
``urn:uuid:`` are read as ordinary strings, so slugs like that still work.

If every strategy you asked for is skipped, for example
``lookup_strategies = ("display_id",)`` on a model with no prefix, no value
could ever match. Instead of a 404 for every request, the lookup raises
``MissingPrefixError``, or ``ImproperlyConfigured`` for a slug-only lookup
without a slug field.

UUID objects
------------

The lookup functions also accept a ``uuid.UUID``. It's already parsed, so it
goes straight to the UUID field and the strategies aren't consulted:

.. code-block:: python

   resolve_object(Invoice, invoice.id, strategies=("slug",))  # still found

The configuration errors above are still raised for UUID objects. The
configuration is wrong whatever the value, so it's reported the first time the
lookup runs, not only for some inputs.
