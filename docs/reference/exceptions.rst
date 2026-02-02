Exceptions
==========

All exceptions inherit from ``DisplayIDLookupError``.

Exception Hierarchy
-------------------

.. code-block:: text

   DisplayIDLookupError
   └── InvalidIdentifierError
   └── UnknownPrefixError
   └── MissingPrefixError
   └── ObjectNotFoundError
   └── AmbiguousIdentifierError

Exception Classes
-----------------

InvalidIdentifierError
~~~~~~~~~~~~~~~~~~~~~~

Raised when the identifier cannot be parsed by any strategy.

.. code-block:: python

   from django_display_ids import InvalidIdentifierError

   try:
       invoice = resolve_object(Invoice, "not-valid-anything", prefix="inv")
   except InvalidIdentifierError:
       # Handle invalid input

UnknownPrefixError
~~~~~~~~~~~~~~~~~~

Raised when a display ID has a prefix that doesn't match the expected one.

.. code-block:: python

   from django_display_ids import UnknownPrefixError

   try:
       # Expecting "inv" but got "usr"
       invoice = resolve_object(Invoice, "usr_2aUyqjCzEIiEcYMKj7TZtw", prefix="inv")
   except UnknownPrefixError as e:
       print(f"Expected prefix: {e.expected}")
       print(f"Got prefix: {e.actual}")

Attributes:

- ``expected`` — The expected prefix
- ``actual`` — The prefix that was received

MissingPrefixError
~~~~~~~~~~~~~~~~~~

Raised when the ``display_id`` strategy is used but no prefix is configured.

.. code-block:: python

   from django_display_ids import MissingPrefixError

   try:
       # No prefix configured
       invoice = resolve_object(Invoice, "inv_xxx", strategies=("display_id",))
   except MissingPrefixError:
       # Configure a prefix

ObjectNotFoundError
~~~~~~~~~~~~~~~~~~~

Raised when no database record matches the resolved identifier.

.. code-block:: python

   from django_display_ids import ObjectNotFoundError

   try:
       invoice = resolve_object(Invoice, "inv_2aUyqjCzEIiEcYMKj7TZtw", prefix="inv")
   except ObjectNotFoundError:
       # Handle not found

AmbiguousIdentifierError
~~~~~~~~~~~~~~~~~~~~~~~~

Raised when multiple records match (typically with slug lookups).

.. code-block:: python

   from django_display_ids import AmbiguousIdentifierError

   try:
       # Multiple invoices have the slug "duplicate-name"
       invoice = resolve_object(
           Invoice, "duplicate-name",
           strategies=("slug",),
           prefix="inv"
       )
   except AmbiguousIdentifierError:
       # Handle ambiguity

Framework-Specific Handling
---------------------------

**Django CBVs** (``DisplayIDMixin``):
   All exceptions are converted to ``Http404``.

**Django REST Framework** (``DisplayIDMixin`` from ``contrib.rest_framework``):
   - ``ObjectNotFoundError`` → ``NotFound`` (404)
   - Other exceptions → ``ParseError`` (400)

**Django Admin** (``DisplayIDAdminSearchMixin``):
   Exceptions are silently caught and the search falls back to normal behavior.
