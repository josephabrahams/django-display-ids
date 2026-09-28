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

The encoders also take a UUID string, in any form ``uuid.UUID()`` accepts.

All four raise ``ValueError`` for bad input: a prefix that isn't 1 to 16
lowercase letters, a string that isn't a UUID, or a display ID or base62
string in the wrong format. The encoders raise ``TypeError`` for a value that's
neither a UUID nor a string.
