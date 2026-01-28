Model Integration
=================

Add display ID support directly to your Django models.

DisplayIDMixin
--------------

Add a ``display_id`` property to your models:

.. code-block:: python

   import uuid
   from django.db import models
   from django_display_ids import DisplayIDMixin

   class Invoice(DisplayIDMixin, models.Model):
       display_id_prefix = "inv"
       id = models.UUIDField(primary_key=True, default=uuid.uuid4)

   invoice = Invoice.objects.first()
   invoice.display_id  # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

Configuration Attributes
~~~~~~~~~~~~~~~~~~~~~~~~

``display_id_prefix``
   **Required.** The prefix for display IDs (1-16 lowercase letters).

``uuid_field``
   The name of the UUID field. Defaults to ``"id"``.

``slug_field``
   The name of the slug field for slug lookups. Defaults to ``"slug"``.

Prefix Registry
~~~~~~~~~~~~~~~

When you define a model with ``DisplayIDMixin``, the prefix is automatically
registered. This allows the library to:

- Validate that display IDs have the correct prefix
- Look up models by prefix using ``get_model_for_prefix()``

Prefix collisions (two models with the same prefix) raise ``ValueError`` at
class definition time.

DisplayIDManager
----------------

Add convenient lookup methods to your model:

.. code-block:: python

   from django_display_ids import DisplayIDMixin, DisplayIDManager

   class Invoice(DisplayIDMixin, models.Model):
       display_id_prefix = "inv"
       objects = DisplayIDManager()
       id = models.UUIDField(primary_key=True, default=uuid.uuid4)

get_by_display_id
~~~~~~~~~~~~~~~~~

Look up by display ID only:

.. code-block:: python

   invoice = Invoice.objects.get_by_display_id("inv_2aUyqjCzEIiEcYMKj7TZtw")

Raises:

- ``InvalidIdentifierError`` — Not a valid display ID format
- ``UnknownPrefixError`` — Prefix doesn't match the model
- ``ObjectNotFoundError`` — No matching record

get_by_identifier
~~~~~~~~~~~~~~~~~

Look up by any supported identifier type:

.. code-block:: python

   # By display ID
   invoice = Invoice.objects.get_by_identifier("inv_2aUyqjCzEIiEcYMKj7TZtw")

   # By UUID
   invoice = Invoice.objects.get_by_identifier("550e8400-e29b-41d4-a716-446655440000")

   # By slug (if slug strategy is enabled)
   invoice = Invoice.objects.get_by_identifier("my-invoice", strategies=("display_id", "uuid", "slug"))

Works with filtered querysets:

.. code-block:: python

   invoice = Invoice.objects.filter(active=True).get_by_identifier("inv_xxx")

Parameters:

``value``
   The identifier to look up.

``strategies``
   Tuple of strategies to try. Defaults to ``("display_id", "uuid")``.

``prefix``
   Expected display ID prefix. Defaults to the model's ``display_id_prefix``.
