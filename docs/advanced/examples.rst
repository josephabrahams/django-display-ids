Example Values
==============

``example_uuid()`` and ``example_display_id()`` return realistic-looking
values for docs and OpenAPI schemas. They're derived from the prefix, so the
same prefix always gives the same value and generated docs don't change
between builds:

.. code-block:: python

   >>> from django_display_ids import example_display_id, example_uuid
   >>> example_uuid("inv")
   UUID('89270a50-341b-b8e8-3734-ee062603c63c')
   >>> example_display_id("inv")
   'inv_4Anmzka0FyCjgdYA5m1D4u'
   >>> example_display_id(Invoice)  # reads Invoice.display_id_prefix
   'inv_4Anmzka0FyCjgdYA5m1D4u'

``DisplayIDField`` and ``DisplayIDRelatedField`` use them for their schema
examples. To use them in your own drf-spectacular examples:

.. code-block:: python

   from drf_spectacular.utils import OpenApiExample, extend_schema

   @extend_schema(
       examples=[
           OpenApiExample(
               "Invoice",
               value={
                   "id": str(example_uuid("inv")),
                   "display_id": example_display_id("inv"),
                   "name": "Q1 invoice",
               },
           ),
       ],
   )
   class InvoiceViewSet(ModelViewSet): ...
