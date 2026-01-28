Example Generation
==================

Generate deterministic example UUIDs and display IDs for documentation and
OpenAPI schemas.

Why Deterministic Examples?
---------------------------

When generating API documentation, you want example values that:

1. **Stay consistent** across documentation regenerations
2. **Match the expected format** (correct prefix, valid base62)
3. **Look realistic** (not obviously fake like ``00000000-...``)

The example functions produce the same output for the same input, making your
docs stable and predictable.

Functions
---------

example_uuid
~~~~~~~~~~~~

Generate a deterministic UUID from a prefix or model.

.. code-block:: python

   from django_display_ids import example_uuid

   # From prefix string
   u = example_uuid("inv")
   # -> UUID('a172cedc-ae47-474b-...')

   # From model class
   u = example_uuid(Invoice)
   # -> same UUID (uses Invoice.display_id_prefix)

The same prefix always produces the same UUID.

example_display_id
~~~~~~~~~~~~~~~~~~

Generate a deterministic display ID from a prefix or model.

.. code-block:: python

   from django_display_ids import example_display_id

   display_id = example_display_id("inv")
   # -> "inv_4ueEO5Nz4X7u9qc3FVHokM"

   display_id = example_display_id(Invoice)
   # -> same display ID

Aliases
~~~~~~~

For backward compatibility, these aliases are also available:

- ``example_uuid_for_prefix`` — alias for ``example_uuid``
- ``example_display_id_for_prefix`` — alias for ``example_display_id``

Usage with drf-spectacular
--------------------------

Use example functions to create consistent OpenAPI schemas:

.. code-block:: python

   from drf_spectacular.utils import extend_schema, OpenApiExample
   from django_display_ids import example_display_id, example_uuid

   @extend_schema(
       examples=[
           OpenApiExample(
               "Invoice Response",
               value={
                   "id": str(example_uuid("inv")),
                   "display_id": example_display_id("inv"),
                   "name": "Q1 2024 Invoice",
               },
           ),
       ],
   )
   class InvoiceViewSet(ModelViewSet):
       ...

The ``DisplayIDField`` serializer field uses these functions automatically
when generating its schema examples.

How It Works
------------

The functions use a deterministic hash of the prefix to generate a UUID.
The algorithm is stable across Python versions and library updates.

.. code-block:: python

   # Simplified implementation concept:
   # 1. Hash the prefix string
   # 2. Use hash bytes to construct a UUID
   # 3. Result is always the same for the same prefix
