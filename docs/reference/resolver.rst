Resolver Functions
==================

Core functions for resolving identifiers to database objects.

resolve_object
--------------

The central resolver function used by all mixins.

.. code-block:: python

   from django_display_ids import resolve_object

   invoice = resolve_object(
       model=Invoice,
       value="inv_2aUyqjCzEIiEcYMKj7TZtw",
       strategies=("display_id", "uuid", "slug"),
       prefix="inv",
   )

Parameters
~~~~~~~~~~

``model``
   The Django model class to query.

``value``
   The identifier string to resolve.

``strategies``
   Tuple of strategy names to try, in order. Defaults to ``("display_id", "uuid")``.

``prefix``
   Expected display ID prefix. Required for the ``display_id`` strategy.

``uuid_field``
   Name of the UUID field on the model. Defaults to ``"id"``.

``slug_field``
   Name of the slug field on the model. Defaults to ``"slug"``.

``queryset``
   Optional pre-filtered queryset. If not provided, uses ``model.objects.all()``.

Return Value
~~~~~~~~~~~~

Returns the matched model instance.

Exceptions
~~~~~~~~~~

- ``InvalidIdentifierError`` — No strategy could parse the identifier
- ``UnknownPrefixError`` — Display ID prefix doesn't match expected
- ``MissingPrefixError`` — ``display_id`` strategy used but no prefix configured
- ``ObjectNotFoundError`` — No database record matches
- ``AmbiguousIdentifierError`` — Multiple records match (slug lookup)

get_model_for_prefix
--------------------

Look up a model class by its registered display ID prefix.

.. code-block:: python

   from django_display_ids.resolver import get_model_for_prefix

   model_class = get_model_for_prefix("inv")
   # -> <class 'myapp.models.Invoice'>

Returns ``None`` if no model is registered with that prefix.

Prefix Registration
~~~~~~~~~~~~~~~~~~~

Prefixes are automatically registered when a model class with
``DisplayIDModel`` is defined. You don't need to manually register prefixes.
