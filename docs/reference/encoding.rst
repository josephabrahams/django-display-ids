Encoding
========

A display ID is a prefix of 1 to 16 lowercase letters, an underscore, and the
UUID in base62 (``0-9``, ``A-Z``, ``a-z``). A UUID is 128 bits, which always
takes 22 base62 characters, so the pattern is ``^[a-z]{1,16}_[0-9A-Za-z]{22}$``.

These functions do the conversion and don't touch the database:

.. code-block:: python

   >>> import uuid
   >>> from django_display_ids import (
   ...     decode_display_id, decode_uuid, encode_display_id, encode_uuid,
   ... )
   >>> value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

   >>> encode_display_id("inv", value)
   'inv_2aUyqjCzEIiEcYMKj7TZtw'
   >>> decode_display_id("inv_2aUyqjCzEIiEcYMKj7TZtw")
   ('inv', UUID('550e8400-e29b-41d4-a716-446655440000'))

   >>> encode_uuid(value)
   '2aUyqjCzEIiEcYMKj7TZtw'
   >>> decode_uuid("2aUyqjCzEIiEcYMKj7TZtw")
   UUID('550e8400-e29b-41d4-a716-446655440000')

The encoders also take a UUID string in the hyphenated form, in either case.

All four raise ``ValueError`` for bad input: a prefix that isn't 1 to 16
lowercase letters, a string that isn't a UUID, or a display ID or base62
string in the wrong format. The encoders raise ``TypeError`` for a value that's
neither a UUID nor a string.

IDs without a model
-------------------

For IDs with no row behind them, like request IDs or event IDs, use
``DisplayIDType``. It has the same format, without a model:

.. code-block:: python

   >>> from django_display_ids import DisplayIDType
   >>> RequestID = DisplayIDType("req")

   >>> RequestID.encode(value)
   'req_2aUyqjCzEIiEcYMKj7TZtw'
   >>> RequestID.parse("req_2aUyqjCzEIiEcYMKj7TZtw")
   UUID('550e8400-e29b-41d4-a716-446655440000')
   >>> RequestID.is_valid("inv_2aUyqjCzEIiEcYMKj7TZtw")
   False
   >>> RequestID.regex
   'req_[0-9A-Za-z]{22}'

   >>> RequestID.generate()  # a new ID, different every time

``generate()`` uses ``uuid.uuid7``, so new IDs sort by when they were made. It
needs Python 3.14+. On 3.12 or 3.13, pass a ``factory``, such as
``DisplayIDType("req", factory=uuid6.uuid7)``, or ``uuid.uuid4`` if the IDs
shouldn't show when they were made. Without one, ``generate()`` raises
``ImproperlyConfigured``. The other methods work on any version.

``parse()`` ignores surrounding whitespace, and raises ``InvalidIdentifierError``
or ``UnknownPrefixError`` (both ``ValueError``) for anything else. ``regex``
has no anchors, so it fits in a URL pattern.

The prefix can't be one a model already uses, and the other way round, so
``DisplayIDType("inv")`` raises ``ValueError`` if ``Invoice`` uses ``inv``.

To search a field holding these IDs in the admin, see
:doc:`/usage/admin`.
