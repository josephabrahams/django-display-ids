Resolver Functions
==================

Core functions for resolving identifiers to database objects.

resolve_object
--------------

The central resolver function used by all mixins.

.. code-block:: python

   from django_display_ids import resolve_object

   # Auto-detects prefix, uuid_field, slug_field, and strategies from the model
   invoice = resolve_object(Invoice, "inv_2aUyqjCzEIiEcYMKj7TZtw")

Parameters
~~~~~~~~~~

``model``
   The Django model class to query.

``value``
   The identifier string to resolve.

``strategies``
   Tuple of strategy names to try, in order. Defaults to ``("display_id", "uuid", "slug")``.

``prefix``
   Expected display ID prefix. When ``None`` (the default), auto-detected
   from the model's ``display_id_prefix`` attribute (set by
   ``DisplayIDModel``).

``uuid_field``
   Name of the UUID field on the model. When ``None`` (the default),
   auto-detected from the model's ``uuid_field`` attribute (set by
   ``DisplayIDModel``), then the ``DISPLAY_IDS["UUID_FIELD"]`` setting,
   then ``"id"``.

``slug_field``
   Name of the slug field on the model. When ``None`` (the default),
   auto-detected from the model's ``slug_field`` attribute (set by
   ``DisplayIDModel``), then the ``DISPLAY_IDS["SLUG_FIELD"]`` setting,
   then ``"slug"``.

``queryset``
   Optional pre-filtered queryset. If not provided, uses ``model.objects.all()``.

Return Value
~~~~~~~~~~~~

Returns the matched model instance.

Exceptions
~~~~~~~~~~

- ``InvalidIdentifierError`` — No strategy could parse the identifier
- ``UnknownPrefixError`` — Display ID prefix doesn't match expected
- ``ObjectNotFoundError`` — No database record matches
- ``AmbiguousIdentifierError`` — Multiple records match (slug lookup)

get_model_for_prefix
--------------------

Look up a model class by its registered display ID prefix.

.. code-block:: python

   from django_display_ids import get_model_for_prefix

   model_class = get_model_for_prefix("inv")
   # -> <class 'myapp.models.Invoice'>

Returns ``None`` if no model is registered with that prefix.

Prefix Registration
~~~~~~~~~~~~~~~~~~~

Prefixes are automatically registered when a model class with
``DisplayIDModel`` is defined. You don't need to manually register prefixes.
