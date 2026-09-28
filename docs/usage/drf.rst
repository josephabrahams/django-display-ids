Django REST Framework
=====================

Install with ``pip install "django-display-ids[drf]"``. Everything here is
imported from ``django_display_ids.contrib.rest_framework``.

Views
-----

Add ``DisplayIDMixin`` to a viewset or generic view:

.. code-block:: python

   from rest_framework.viewsets import ModelViewSet
   from django_display_ids.contrib.rest_framework import DisplayIDMixin

   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       queryset = Invoice.objects.all()
       serializer_class = InvoiceSerializer
       lookup_url_kwarg = "id"

It also works on a plain ``APIView`` that defines ``get_queryset()``.

``get_object()`` works like DRF's own. It runs ``filter_queryset()`` first, so
filter backends apply, and it checks object permissions. An identifier that
can't be parsed, has another model's prefix, or matches nothing gives a 404. A
slug that matches more than one row raises ``MultipleObjectsReturned``, and a
missing URL keyword argument raises ``AssertionError``, both as in DRF.

The mixin takes the same attributes as the Django view mixin
(``lookup_strategies``, ``display_id_prefix``, ``uuid_field``,
``slug_field``). See :doc:`/reference/settings`.

DisplayIDField
--------------

Adds an object's display ID to a response:

.. code-block:: python

   from django_display_ids.contrib.rest_framework import DisplayIDField

   class InvoiceSerializer(serializers.ModelSerializer):
       display_id = DisplayIDField()

       class Meta:
           model = Invoice
           fields = ("id", "display_id", "name")

   # {"id": "550e8400-...", "display_id": "inv_2aUyqjCzEIiEcYMKj7TZtw", ...}

It's read-only. The prefix comes from, in order:

1. ``prefix="inv"`` on the field.
2. ``prefix_from=Invoice``, which reads another model's prefix. Use it when
   the serialized object isn't an ``Invoice`` itself, such as a row from a
   database view built from invoices.
3. The serialized object's ``display_id_prefix``.

If there's no prefix, the field raises ``ValueError``. Pass ``required=False``
to get ``None`` instead, for serializers that handle a mix of models.

DisplayIDRelatedField
---------------------

A writable related field, like ``PrimaryKeyRelatedField`` but with display IDs:

.. code-block:: python

   from django_display_ids.contrib.rest_framework import DisplayIDRelatedField

   class OrderSerializer(serializers.ModelSerializer):
       customer = DisplayIDRelatedField(queryset=Customer.objects.all())
       tags = DisplayIDRelatedField(queryset=Tag.objects.all(), many=True)

       class Meta:
           model = Order
           fields = ("customer", "tags")

   # {"customer": "cust_2aUyqjCzEIiEcYMKj7TZtw", "tags": ["tag_..."]}

Responses show the related object's display ID. Requests accept a display ID,
UUID or slug, parsed like the view mixins do, so clients can send back what
they read. Anything that doesn't match fails validation with the
``does_not_exist`` error code. A slug that matches more than one row raises
``MultipleObjectsReturned``, as ``SlugRelatedField`` does.

To accept display IDs only, pass ``lookup_strategies=("display_id",)``. The
field takes the same options as the view mixins as keyword arguments.

The related model needs a prefix, or pass ``display_id_prefix=``. Otherwise
the serializer raises ``MissingPrefixError`` when it's defined.

When the related model's UUID is its primary key, the display ID is built from
the foreign key column without a query. Otherwise each related object is
loaded, so add ``select_related()`` or ``prefetch_related()`` to the view's
queryset.

OpenAPI schemas
---------------

With ``pip install "django-display-ids[spectacular]"``, drf-spectacular
documents both fields:

- ``DisplayIDField`` is a string with the display ID pattern and a realistic
  example. The prefix comes from the field, the serializer's model, or the
  view's queryset.
- ``DisplayIDRelatedField`` shows a display ID in responses. In requests the
  description lists what the field accepts, for example "Identifier:
  display_id (cust_xxx), UUID, or slug". A display-ID-only field also gets a
  pattern, so clients can validate before sending.

For identifiers in URL paths, ``id_param_description()`` builds the same kind
of description. By default it lists the formats in the ``STRATEGIES`` setting:

.. code-block:: python

   from django_display_ids.contrib.drf_spectacular import id_param_description
   from drf_spectacular.utils import OpenApiParameter, extend_schema

   @extend_schema(
       parameters=[
           OpenApiParameter(
               "id",
               str,
               OpenApiParameter.PATH,
               description=id_param_description("inv"),
               # "Identifier: display_id (inv_xxx), UUID, or slug"
           )
       ],
   )
   class InvoiceViewSet(DisplayIDMixin, ModelViewSet): ...

If the view sets its own ``lookup_strategies``, pass ``with_uuid=`` and
``with_slug=`` to match.
