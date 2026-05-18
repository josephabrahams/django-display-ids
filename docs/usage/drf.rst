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

- ``ObjectNotFoundError`` → ``NotFound`` (404)
- ``InvalidIdentifierError`` → ``ParseError`` (400)
- ``UnknownPrefixError`` → ``ParseError`` (400)

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

OpenAPI / drf-spectacular
-------------------------

When drf-spectacular is installed, ``DisplayIDField`` automatically generates
proper schema with prefix-specific examples. No configuration needed.

The extension resolves the prefix from (in order):

1. Field's ``prefix=`` or ``prefix_from=`` argument
2. Serializer's ``Meta.model.display_id_prefix``
3. View's queryset model

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
               # -> "Identifier: display_id (inv_xxx) or UUID"
           )
       ],
   )
   class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
       ...

For endpoints that also accept slugs:

.. code-block:: python

   description=id_param_description("app", with_slug=True)
   # -> "Identifier: display_id (app_xxx), UUID, or slug"

For display ID only (no UUID fallback):

.. code-block:: python

   description=id_param_description("inv", with_uuid=False)
   # -> "Identifier: display_id (inv_xxx)"
