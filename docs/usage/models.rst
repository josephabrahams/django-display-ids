Models
======

DisplayIDModel
--------------

Subclass ``DisplayIDModel`` and set a prefix:

.. code-block:: python

   import uuid

   from django.db import models
   from django_display_ids import DisplayIDManager, DisplayIDModel

   class Invoice(DisplayIDModel):
       display_id_prefix = "inv"

       id = models.UUIDField(primary_key=True, default=uuid.uuid7)
       slug = models.SlugField(unique=True)

       objects = DisplayIDManager()

   invoice.display_id  # "inv_2aUyqjCzEIiEcYMKj7TZtw"

``uuid.uuid7`` needs Python 3.14+. Its UUIDs start with a timestamp, so new
rows go at the end of the index instead of all over it, as random ``uuid4``
values do. On Python 3.12 or 3.13, ``from uuid6 import uuid7`` from the
`uuid6 <https://pypi.org/project/uuid6/>`_ package works the same way.

``display_id`` is ``None`` while the UUID field is empty, and on models that
don't set a prefix.

``DisplayIDModel`` is abstract and adds no fields, so it needs no migration.
It reads three class attributes:

``display_id_prefix``
   1 to 16 lowercase letters. Two models can't use the same prefix: defining the
   second one raises ``ValueError``.

``uuid_field``
   The field holding the UUID, if it isn't ``id``. For example, a model with
   a big-integer primary key and ``uid = models.UUIDField(...)`` sets
   ``uuid_field = "uid"``.

``slug_field``
   The field slugs are looked up in, if it isn't ``slug``.

If a model doesn't set ``uuid_field`` or ``slug_field``, the
``DISPLAY_IDS["UUID_FIELD"]`` and ``DISPLAY_IDS["SLUG_FIELD"]`` settings are
used. See :doc:`/reference/settings`.

``get_model_for_prefix("inv")`` returns the name of the model registered for a
prefix (``"Invoice"``), or ``None``.

DisplayIDManager
----------------

``DisplayIDManager`` adds lookup methods to ``Model.objects``. They're also on
querysets, so they respect any filtering:

.. code-block:: python

   Invoice.objects.filter(customer=customer).get_by_identifier(value)

The single-object methods raise ``Invoice.DoesNotExist`` for anything that
doesn't match, including unparseable input and display IDs with another
model's prefix, the same as ``Invoice.objects.get()``.

get_by_identifier
~~~~~~~~~~~~~~~~~

Accepts a display ID, a UUID (string or ``uuid.UUID``) or a slug:

.. code-block:: python

   Invoice.objects.get_by_identifier("inv_2aUyqjCzEIiEcYMKj7TZtw")
   Invoice.objects.get_by_identifier("550e8400-e29b-41d4-a716-446655440000")
   Invoice.objects.get_by_identifier("march-invoice")

It takes ``strategies=`` and ``prefix=`` to override the defaults for one call.

get_by_display_id
~~~~~~~~~~~~~~~~~

Accepts only display IDs (and ``uuid.UUID`` objects). On a model without a
prefix it raises ``MissingPrefixError``, since no display ID could ever match.

resolve_uuid
~~~~~~~~~~~~

Returns the UUID without loading the object:

.. code-block:: python

   Invoice.objects.resolve_uuid("inv_2aUyqjCzEIiEcYMKj7TZtw")
   # UUID('550e8400-e29b-41d4-a716-446655440000')

Display IDs and UUIDs are decoded without a query, and the row isn't checked
to exist. Slugs need one query. This is handy for cursor pagination, where you
only need the UUID for a ``WHERE`` clause.

Like the other manager methods, it raises ``Invoice.DoesNotExist`` for a value
no strategy can read, even though it doesn't query the database for it. With
the default strategies that includes a display ID with another prefix. If
``slug`` comes first, any string is read as a slug, so that value is looked up
as a slug instead.

get_by_identifiers
~~~~~~~~~~~~~~~~~~

Looks up several objects in one query and returns a queryset:

.. code-block:: python

   Invoice.objects.get_by_identifiers([
       "inv_2aUyqjCzEIiEcYMKj7TZtw",
       "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
       "march-invoice",
   ]).order_by("created")

Like ``filter()``, it leaves out identifiers that match nothing. That includes
unparseable ones and display IDs with the wrong prefix. The results aren't in
input order. To see which identifier found which object, use
``resolve_objects()`` (see :doc:`/reference/resolver`).
