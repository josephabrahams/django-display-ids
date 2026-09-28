Settings Reference
==================

Django Settings
---------------

All settings are optional and have sensible defaults. Configure them in your
Django settings module:

.. code-block:: python

   # settings.py
   DISPLAY_IDS = {
       "UUID_FIELD": "id",
       "SLUG_FIELD": "slug",
       "STRATEGIES": ("display_id", "uuid", "slug"),
       "SLUG_REGEX": r"[-a-zA-Z0-9_]+",
   }

Available Settings
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Setting
     - Default
     - Description
   * - ``UUID_FIELD``
     - ``"id"``
     - Default UUID field name for lookups
   * - ``SLUG_FIELD``
     - ``"slug"``
     - Default slug field name for lookups
   * - ``STRATEGIES``
     - ``("display_id", "uuid", "slug")``
     - Default lookup strategies (in order)
   * - ``SLUG_REGEX``
     - ``[-a-zA-Z0-9_]+``
     - Regex pattern for slug matching in URL converters

SLUG_REGEX
~~~~~~~~~~

The ``SLUG_REGEX`` setting controls what patterns are considered valid slugs
in the :class:`~django_display_ids.converters.DisplayIDOrSlugConverter` and
:class:`~django_display_ids.converters.DisplayIDOrUUIDOrSlugConverter`.
It's read when Django builds your URL patterns, so ``override_settings`` in
tests works as expected.

By default, it uses Django's slug pattern (``[-a-zA-Z0-9_]+``), which allows:

- Letters (uppercase and lowercase)
- Numbers
- Hyphens
- Underscores

To restrict to lowercase slugs only:

.. code-block:: python

   DISPLAY_IDS = {
       "SLUG_REGEX": r"[a-z0-9-]+",
   }

To allow dots in slugs:

.. code-block:: python

   DISPLAY_IDS = {
       "SLUG_REGEX": r"[-a-zA-Z0-9_.]+",
   }

View/Mixin Attributes
---------------------

All mixins accept these attributes to override defaults:

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Attribute
     - Default
     - Description
   * - ``lookup_url_kwarg``
     - ``"pk"``
     - URL parameter name to read
   * - ``lookup_strategies``
     - from settings
     - Tuple of strategies to try
   * - ``display_id_prefix``
     - from model
     - Expected display ID prefix
   * - ``uuid_field``
     - from model, then settings
     - UUID field name on model
   * - ``slug_field``
     - from model, then settings
     - Slug field name on model

Model Class Attributes
----------------------

Models using ``DisplayIDModel`` can define:

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Attribute
     - Required
     - Description
   * - ``display_id_prefix``
     - Yes
     - Prefix for display IDs (1-16 lowercase letters)
   * - ``uuid_field``
     - No
     - Override default UUID field name
   * - ``slug_field``
     - No
     - Override default slug field name

Attribute Precedence
--------------------

When resolving ``uuid_field`` and ``slug_field``, these are checked in order:

1. View/mixin attribute (e.g., ``self.uuid_field``)
2. Model class attribute (e.g., ``Model.uuid_field``)
3. Django settings (``DISPLAY_IDS["UUID_FIELD"]``)
4. Built-in default

``display_id_prefix`` comes from the view/mixin attribute, then the model.
There is no setting for it. ``lookup_strategies`` comes from the view/mixin
attribute, then the ``DISPLAY_IDS["STRATEGIES"]`` setting. There is no model
attribute for it.

This allows you to set project-wide defaults in settings while overriding
specific views or models as needed.
