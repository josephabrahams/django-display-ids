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
       "STRATEGIES": ("display_id", "uuid"),
   }

Available Settings
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 15 60
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
     - ``("display_id", "uuid")``
     - Default lookup strategies (in order)

View/Mixin Attributes
---------------------

All mixins accept these attributes to override defaults:

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Attribute
     - Default
     - Description
   * - ``lookup_param`` / ``lookup_url_kwarg``
     - ``"pk"``
     - URL parameter name to read
   * - ``lookup_strategies``
     - from settings
     - Tuple of strategies to try
   * - ``display_id_prefix``
     - from model
     - Expected display ID prefix
   * - ``uuid_field``
     - ``"id"``
     - UUID field name on model
   * - ``slug_field``
     - ``"slug"``
     - Slug field name on model

Model Class Attributes
----------------------

Models using ``DisplayIDMixin`` can define:

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

When resolving configuration, attributes are checked in this order:

1. View/mixin attribute (e.g., ``self.display_id_prefix``)
2. Model class attribute (e.g., ``Model.display_id_prefix``)
3. Django settings (``DISPLAY_IDS["..."]``)
4. Built-in default

This allows you to set project-wide defaults in settings while overriding
specific views or models as needed.
