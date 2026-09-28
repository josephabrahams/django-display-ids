Resolver
========

resolve_object
--------------

Looks up an object from any identifier, outside a view:

.. code-block:: python

   from django_display_ids import resolve_object

   invoice = resolve_object(Invoice, "inv_2aUyqjCzEIiEcYMKj7TZtw")
   invoice = resolve_object(Invoice, value, queryset=Invoice.objects.filter(paid=True))

``resolve_object(model, value, *, strategies=None, prefix=None, uuid_field=None, slug_field=None, queryset=None)``

``value`` is a string or a ``uuid.UUID``. The keyword arguments override the
model's settings for this call, as described in :doc:`settings`. Without
``queryset``, it searches ``model._default_manager.all()``.

It raises the library's own exceptions, rather than ``Model.DoesNotExist`` like
the manager methods:

- ``InvalidIdentifierError`` if no strategy can read the value
- ``UnknownPrefixError`` if a display ID has another prefix
- ``ObjectNotFoundError`` if nothing matches
- ``AmbiguousIdentifierError`` if a slug matches more than one row
- ``MissingPrefixError`` or ``ImproperlyConfigured`` if the strategies can
  never be used for the model
- ``TypeError`` if ``queryset`` is for a different model

Each one also subclasses the matching Django or Python exception, so existing
``except`` clauses still work. See :doc:`exceptions`.

get_model_for_prefix
--------------------

Returns the name of the model registered for a prefix, or ``None``:

.. code-block:: python

   >>> from django_display_ids import get_model_for_prefix
   >>> get_model_for_prefix("inv")
   'Invoice'

Prefixes are registered when a ``DisplayIDModel`` subclass is defined.
