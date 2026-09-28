Django REST Framework
=====================

Full integration with Django REST Framework views and serializers.

DisplayIDMixin
--------------------

For ViewSets
~~~~~~~~~~~~

When your model extends ``DisplayIDModel``, the prefix is inherited
automatically:

.. code-block:: python

   from rest_framework.viewsets import ModelViewSet
   from django_display_ids.contrib.rest_framework import DisplayIDMixin

   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       queryset = Invoice.objects.all()
       serializer_class = InvoiceSerializer
       lookup_url_kwarg = "id"

For APIView
~~~~~~~~~~~

.. code-block:: python

   from rest_framework.views import APIView
   from rest_framework.response import Response
   from django_display_ids.contrib.rest_framework import DisplayIDMixin

   class InvoiceView(DisplayIDMixin, APIView):
       lookup_url_kwarg = "id"

       def get_queryset(self):
           return Invoice.objects.all()

       def get(self, request, *args, **kwargs):
           invoice = self.get_object()
           return Response({"id": str(invoice.id)})

Configuration Attributes
~~~~~~~~~~~~~~~~~~~~~~~~

``lookup_url_kwarg``
   The URL parameter name. Defaults to ``"pk"``.

``lookup_strategies``
   Tuple of strategies to try. Defaults to ``("display_id", "uuid", "slug")``.

``display_id_prefix``
   Expected prefix. When ``None`` (the default), auto-detected by
   ``resolve_object`` from the model's ``display_id_prefix`` attribute.

``uuid_field``
   UUID field name. When ``None`` (the default), auto-detected by
   ``resolve_object`` from the model's ``uuid_field`` attribute, then
   the ``DISPLAY_IDS["UUID_FIELD"]`` setting, then ``"id"``.

``slug_field``
   Slug field name. When ``None`` (the default), auto-detected by
   ``resolve_object`` from the model's ``slug_field`` attribute, then
   the ``DISPLAY_IDS["SLUG_FIELD"]`` setting, then ``"slug"``.

Error Handling
~~~~~~~~~~~~~~

``get_object()`` behaves like DRF's own ``GenericAPIView.get_object()``:

- The queryset goes through ``filter_queryset()`` before the lookup.
- An unparseable identifier, a wrong prefix, or no match all raise ``Http404``,
  which DRF returns as a 404 response.
- A slug that matches more than one row raises ``MultipleObjectsReturned``.
- A missing URL keyword argument fails an ``AssertionError``.

DisplayIDField
--------------

Include display IDs in your API responses:

.. code-block:: python

   from rest_framework import serializers
   from django_display_ids.contrib.rest_framework import DisplayIDField

   class InvoiceSerializer(serializers.Serializer):
       id = serializers.UUIDField(read_only=True)
       display_id = DisplayIDField()
       name = serializers.CharField()

   # Output: {"id": "...", "display_id": "inv_2aUyqjCzEIiEcYMKj7TZtw", ...}

The field reads the prefix from the model's ``display_id_prefix``. Override it
explicitly:

.. code-block:: python

   display_id = DisplayIDField(prefix="inv")

The prefix must be 1-16 lowercase letters. Invalid prefixes raise ``ValueError``
at initialization.

When to use ``prefix_from``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes the row being serialized is a *projection* of another model — for
example a database-view-backed report row that mirrors ``Invoice`` data but is
not an ``Invoice`` instance and carries no ``display_id_prefix`` of its own. In
that case, point the field at the source model rather than hardcoding its
prefix string:

.. code-block:: python

   class InvoiceReportSerializer(serializers.ModelSerializer):
       # InvoiceReport is a view-backed projection of Invoice.
       display_id = DisplayIDField(prefix_from=Invoice)

       class Meta:
           model = InvoiceReport
           fields = ("display_id", "total", "issued_on")

``prefix_from=Invoice`` reads ``Invoice.display_id_prefix`` dynamically — it is
equivalent to ``prefix="inv"`` but stays in sync if the model's prefix changes.
``prefix`` and ``prefix_from`` are mutually exclusive. If ``prefix_from`` points
at a class with no ``display_id_prefix``, a ``ValueError`` is raised at
initialization (app startup), not on the first request.

Tolerating a missing prefix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default the field raises ``ValueError`` when no prefix can be resolved for an
instance. When a single serializer handles heterogeneous rows — only some of
which carry a prefix — pass ``required=False`` to return ``None`` instead:

.. code-block:: python

   display_id = DisplayIDField(required=False)

Resolution precedence
~~~~~~~~~~~~~~~~~~~~~~

The field resolves the prefix from (in order):

1. Field's ``prefix=`` argument
2. Field's ``prefix_from=`` model class
3. The serialized instance's ``display_id_prefix`` attribute

If none resolve, the field raises ``ValueError`` unless ``required=False`` was
passed, in which case it returns ``None``.

DisplayIDRelatedField
---------------------

``DisplayIDField`` only outputs a display ID. To accept one back, for example
to set a foreign key, use ``DisplayIDRelatedField``. It works like DRF's
``PrimaryKeyRelatedField``, but speaks display IDs:

.. code-block:: python

   from django_display_ids.contrib.rest_framework import DisplayIDRelatedField

   class OrderSerializer(serializers.ModelSerializer):
       customer = DisplayIDRelatedField(queryset=Customer.objects.all())
       tags = DisplayIDRelatedField(queryset=Tag.objects.all(), many=True)

       class Meta:
           model = Order
           fields = ("customer", "tags")

   # Output: {"customer": "cust_2aUyqjCzEIiEcYMKj7TZtw", "tags": ["tag_..."]}

Responses show the related object's display ID. Requests accept a display ID,
a UUID, or a slug, parsed with the same rules as the view mixins, so a client
can send back exactly what it read. An identifier that doesn't match, can't be
parsed, or has another model's prefix fails validation with
``does_not_exist``.

The related model needs a ``display_id_prefix``. Otherwise the field raises
``MissingPrefixError`` when the serializer is defined, unless you pass
``display_id_prefix=``. The field also takes ``lookup_strategies``,
``uuid_field`` and ``slug_field``, with the same defaults as the view mixins.

When the related model's UUID is its primary key, the display ID is built from
the foreign key column, so serializing a list doesn't query each related
object. ``PrimaryKeyRelatedField`` does the same. When the UUID is a separate
field, each related object is loaded, as with ``SlugRelatedField``, so use
``select_related()`` (or ``prefetch_related()`` for ``many=True``) in the
view's queryset.

OpenAPI / drf-spectacular
-------------------------

When drf-spectacular is installed, ``DisplayIDField`` automatically generates
proper schema with prefix-specific examples. No configuration needed.

The extension resolves the prefix from (in order):

1. Field's ``prefix=`` or ``prefix_from=`` argument
2. Serializer's ``Meta.model.display_id_prefix``
3. View's queryset model

``DisplayIDRelatedField`` gets a schema too. In responses it's a display ID
with the related model's prefix. In requests the description lists the
formats the field accepts, such as "Identifier: display_id (cust_xxx), UUID,
or slug". If the field only accepts display IDs
(``lookup_strategies=("display_id",)``), the request schema also includes the
display ID pattern with that prefix, so clients can check the format before
sending. With ``many=True`` it's an array of these.

Path Parameter Descriptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the provided helper for consistent API documentation:

.. code-block:: python

   from django_display_ids.contrib.drf_spectacular import id_param_description
   from drf_spectacular.utils import extend_schema, OpenApiParameter
   from drf_spectacular.types import OpenApiTypes

   @extend_schema(
       parameters=[
           OpenApiParameter(
               "id",
               OpenApiTypes.STR,
               OpenApiParameter.PATH,
               description=id_param_description("inv"),
               # -> "Identifier: display_id (inv_xxx), UUID, or slug"
           )
       ],
   )
   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       ...

By default the description lists the formats in the ``STRATEGIES`` setting.
If a view sets its own ``lookup_strategies``, pass ``with_uuid`` and
``with_slug`` to match:

.. code-block:: python

   description=id_param_description("inv", with_slug=False)
   # -> "Identifier: display_id (inv_xxx) or UUID"

   description=id_param_description("inv", with_uuid=False, with_slug=False)
   # -> "Identifier: display_id (inv_xxx)"
