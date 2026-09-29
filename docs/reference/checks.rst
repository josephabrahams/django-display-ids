System checks
=============

``manage.py check`` warns about configuration that would otherwise only fail
when a request hits it. The checks run for every ``DisplayIDModel`` and every
``ModelAdmin`` using ``DisplayIDAdminSearchMixin``, whether or not the app is in
``INSTALLED_APPS``.

.. list-table::
   :header-rows: 1

   * - ID
     - Warns when
   * - ``display_ids.W001``
     - A model has a ``display_id_prefix``, but its ``uuid_field`` isn't a
       ``UUIDField``. This includes the default, ``id``, on a model with an
       integer primary key.
   * - ``display_ids.W002``
     - The ``slug`` strategy is in ``DISPLAY_IDS["STRATEGIES"]``, but the slug
       field isn't unique, so two rows with the same slug make a lookup raise
       ``MultipleObjectsReturned``. ``unique=True``, ``unique_together`` or a
       ``UniqueConstraint`` that includes the field all count, including one
       shared with other fields, such as unique per tenant.
   * - ``display_ids.W003``
     - The admin mixin searches by UUID, but its ``uuid_field`` isn't a
       ``UUIDField``, so every admin search fails.
   * - ``display_ids.W004``
     - A ``display_id_search_fields`` key doesn't end at a ``UUIDField``. For
       example ``customer_id`` when Customer's primary key is an integer; use
       ``customer__uid`` instead.
   * - ``display_ids.W005``
     - The admin mixin's lookup options can never match, for example
       ``lookup_strategies = ("display_id",)`` on a model without a prefix.

These are warnings for now, so upgrading doesn't break a deploy. To turn one
off, add it to ``SILENCED_SYSTEM_CHECKS``.

Views aren't checked, since their model often comes from ``get_queryset()``.
Their misconfigurations still raise on the first request.
