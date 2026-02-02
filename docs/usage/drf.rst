Django REST Framework
=====================

Full integration with Django REST Framework views and serializers.

DisplayIDLookupMixin
--------------------

For ViewSets
~~~~~~~~~~~~

.. code-block:: python

   from rest_framework.viewsets import ModelViewSet
   from django_display_ids.contrib.rest_framework import DisplayIDLookupMixin

   class InvoiceViewSet(DisplayIDLookupMixin, ModelViewSet):
       queryset = Invoice.objects.all()
       serializer_class = InvoiceSerializer
       lookup_url_kwarg = "id"
       lookup_strategies = ("display_id", "uuid")
       display_id_prefix = "inv"

For APIView
~~~~~~~~~~~

.. code-block:: python

   from rest_framework.views import APIView
   from rest_framework.response import Response
   from django_display_ids.contrib.rest_framework import DisplayIDLookupMixin

   class InvoiceView(DisplayIDLookupMixin, APIView):
       lookup_url_kwarg = "id"
       lookup_strategies = ("display_id", "uuid")
       display_id_prefix = "inv"

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
   Tuple of strategies to try. Defaults to ``("display_id", "uuid")``.

``display_id_prefix``
   Expected prefix. Falls back to model's ``display_id_prefix``.

``uuid_field``
   UUID field name. Defaults to ``"id"``.

``slug_field``
   Slug field name. Defaults to ``"slug"``.

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

OpenAPI / drf-spectacular
-------------------------

When drf-spectacular is installed, ``DisplayIDField`` automatically generates
proper schema with prefix-specific examples. No configuration needed.

The extension resolves the prefix from (in order):

1. Field's ``prefix=`` argument
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
   class InvoiceViewSet(DisplayIDLookupMixin, ModelViewSet):
       ...

For endpoints that also accept slugs:

.. code-block:: python

   description=id_param_description("app", with_slug=True)
   # -> "Identifier: display_id (app_xxx), UUID, or slug"

For display ID only (no UUID fallback):

.. code-block:: python

   description=id_param_description("inv", with_uuid=False)
   # -> "Identifier: display_id (inv_xxx)"
