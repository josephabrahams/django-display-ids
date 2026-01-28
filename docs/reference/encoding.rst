Encoding Functions
==================

Low-level functions for encoding and decoding display IDs.

UUID Encoding
-------------

encode_uuid
~~~~~~~~~~~

Encode a UUID to a 22-character base62 string.

.. code-block:: python

   from django_display_ids import encode_uuid
   import uuid

   u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
   encoded = encode_uuid(u)  # -> "2aUyqjCzEIiEcYMKj7TZtw"

decode_uuid
~~~~~~~~~~~

Decode a base62 string back to a UUID.

.. code-block:: python

   from django_display_ids import decode_uuid

   u = decode_uuid("2aUyqjCzEIiEcYMKj7TZtw")
   # -> UUID("550e8400-e29b-41d4-a716-446655440000")

Raises ``ValueError`` if the string is not valid base62 or wrong length.

Display ID Encoding
-------------------

encode_display_id
~~~~~~~~~~~~~~~~~

Create a display ID from a prefix and UUID.

.. code-block:: python

   from django_display_ids import encode_display_id
   import uuid

   invoice_id = uuid.uuid4()
   display_id = encode_display_id("inv", invoice_id)
   # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

Parameters:

``prefix``
   1-16 lowercase letters.

``uuid``
   A UUID object.

Raises ``ValueError`` if the prefix is invalid.

decode_display_id
~~~~~~~~~~~~~~~~~

Extract the prefix and UUID from a display ID.

.. code-block:: python

   from django_display_ids import decode_display_id

   prefix, u = decode_display_id("inv_2aUyqjCzEIiEcYMKj7TZtw")
   # prefix -> "inv"
   # u -> UUID("550e8400-e29b-41d4-a716-446655440000")

Raises ``InvalidIdentifierError`` if the format is invalid.

Display ID Format
-----------------

A display ID consists of:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Component
     - Description
   * - Prefix
     - 1-16 lowercase letters (``[a-z]{1,16}``)
   * - Separator
     - Underscore (``_``)
   * - Encoded UUID
     - 22 base62 characters (``[0-9A-Za-z]{22}``)

**Pattern:** ``^[a-z]{1,16}_[0-9A-Za-z]{22}$``

**Example:** ``inv_2aUyqjCzEIiEcYMKj7TZtw``

Base62 Alphabet
~~~~~~~~~~~~~~~

The base62 encoding uses: ``0-9``, ``A-Z``, ``a-z`` (62 characters total).

UUIDs are 128 bits, which requires exactly 22 base62 characters to represent.
