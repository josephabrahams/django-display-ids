Settings and Options
====================

Lookup options
--------------

Every lookup (the view mixins, the admin mixin, ``DisplayIDRelatedField``,
``resolve_object()`` and the manager methods) uses the same four options. For
each one, the most specific setting wins:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Option
     - On a view, admin or field
     - Function argument
     - On the model
     - Project setting, then default
   * - Strategies to try, in order
     - ``lookup_strategies``
     - ``strategies=``
     - (none)
     - ``STRATEGIES``, ``("display_id", "uuid", "slug")``
   * - Display ID prefix
     - ``display_id_prefix``
     - ``prefix=``
     - ``display_id_prefix``
     - (none)
   * - UUID field
     - ``uuid_field``
     - ``uuid_field=``
     - ``uuid_field``
     - ``UUID_FIELD``, ``"id"``
   * - Slug field
     - ``slug_field``
     - ``slug_field=``
     - ``slug_field``
     - ``SLUG_FIELD``, ``"slug"``

The manager methods take ``strategies=`` and ``prefix=``; they read the fields
from the model. ``DisplayIDRelatedField`` takes the options as keyword
arguments, such as ``DisplayIDRelatedField(queryset=..., lookup_strategies=...)``.

A strategy the model can't support is skipped: ``display_id`` without a prefix,
``slug`` without the slug field. If that leaves nothing to try, the lookup
raises ``MissingPrefixError`` or ``ImproperlyConfigured``. See
:doc:`/advanced/strategies`.

The view mixins also take ``lookup_url_kwarg``, the URL parameter holding the
identifier (default ``"pk"``).

Project settings
----------------

All settings are optional. Set only the ones you want to change:

.. code-block:: python

   # settings.py
   DISPLAY_IDS = {
       "UUID_FIELD": "uid",
       "STRATEGIES": ("display_id", "uuid"),
   }

``UUID_FIELD``
   UUID field name for models that don't set ``uuid_field``. Default ``"id"``.

``SLUG_FIELD``
   Slug field name for models that don't set ``slug_field``. Default ``"slug"``.

``STRATEGIES``
   Strategies to try when a lookup doesn't set its own. Default
   ``("display_id", "uuid", "slug")``.

``SLUG_REGEX``
   What ``DisplayIDOrSlugConverter`` and ``DisplayIDOrUUIDOrSlugConverter``
   accept as a slug in a URL. Default is Django's slug pattern,
   ``[-a-zA-Z0-9_]+``. For lowercase slugs only, use ``r"[a-z0-9-]+"``. It's
   read when Django builds your URL patterns, so ``override_settings`` works in
   tests.
