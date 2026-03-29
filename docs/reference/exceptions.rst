Exceptions
==========

All exceptions inherit from both ``DisplayIDLookupError`` **and** a standard
Django/Python exception, so you can catch them with either:

.. code-block:: python

   from django_display_ids import ObjectNotFoundError

   # Catch with library-specific type
   except ObjectNotFoundError: ...

   # Or catch with Django's built-in type
   except ObjectDoesNotExist: ...

Exception Hierarchy
-------------------

.. code-block:: text

   DisplayIDLookupError
   ├── InvalidIdentifierError     (+ ValueError)
   ├── UnknownPrefixError         (+ ValueError)
   ├── MissingPrefixError         (+ ImproperlyConfigured)
   ├── ObjectNotFoundError        (+ ObjectDoesNotExist)
   └── AmbiguousIdentifierError   (+ MultipleObjectsReturned)

Django/Python Base Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~

Each exception inherits from the Django or Python exception that best matches
its semantics:

.. list-table::
   :header-rows: 1

   * - Exception
     - Django/Python Base
     - Why
   * - ``InvalidIdentifierError``
     - ``ValueError``
     - Bad input — can't parse the identifier
   * - ``UnknownPrefixError``
     - ``ValueError``
     - Bad input — wrong prefix
   * - ``MissingPrefixError``
     - ``ImproperlyConfigured``
     - Configuration problem — no prefix set
   * - ``ObjectNotFoundError``
     - ``ObjectDoesNotExist``
     - No matching database record
   * - ``AmbiguousIdentifierError``
     - ``MultipleObjectsReturned``
     - Multiple records match

This means existing ``except`` clauses work naturally:

.. code-block:: python

   from django.core.exceptions import ObjectDoesNotExist

   try:
       invoice = Invoice.objects.get_by_identifier("inv_xxx")
   except ObjectDoesNotExist:
       # Catches ObjectNotFoundError from display ID lookups
       # AND model.DoesNotExist from regular .get() calls
       ...

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
   except ValueError:
       # Also works — InvalidIdentifierError IS a ValueError

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

Raised when a display ID operation is attempted on a model without a prefix.

.. code-block:: python

   from django_display_ids import MissingPrefixError

   try:
       # Order has no display_id_prefix
       order = Order.objects.get_by_display_id("ord_xxx")
   except MissingPrefixError:
       # Configure a prefix on the model
   except ImproperlyConfigured:
       # Also works

ObjectNotFoundError
~~~~~~~~~~~~~~~~~~~

Raised when no database record matches the resolved identifier.

.. code-block:: python

   from django_display_ids import ObjectNotFoundError

   try:
       invoice = resolve_object(Invoice, "inv_2aUyqjCzEIiEcYMKj7TZtw", prefix="inv")
   except ObjectNotFoundError:
       # Handle not found
   except ObjectDoesNotExist:
       # Also works — same as Django's model.DoesNotExist

AmbiguousIdentifierError
~~~~~~~~~~~~~~~~~~~~~~~~

Raised when multiple records match (typically with slug lookups).

.. code-block:: python

   from django_display_ids import AmbiguousIdentifierError

   try:
       # Multiple invoices have the slug "duplicate-name"
       invoice = resolve_object(Invoice, "duplicate-name", strategies=("slug",))
   except AmbiguousIdentifierError:
       # Handle ambiguity
   except MultipleObjectsReturned:
       # Also works

QuerySet Methods
----------------

``DisplayIDQuerySet`` methods (``get_by_display_id``, ``get_by_identifier``)
raise ``Model.DoesNotExist`` and ``Model.MultipleObjectsReturned``, matching
Django's ``QuerySet.get()`` contract:

.. code-block:: python

   try:
       invoice = Invoice.objects.get_by_identifier("inv_xxx")
   except Invoice.DoesNotExist:
       # Same as Invoice.objects.get(slug="xxx") — natural Django pattern

The library's typed exceptions (``ObjectNotFoundError``, ``InvalidIdentifierError``,
etc.) are still raised by lower-level functions like ``resolve_object()`` and
``parse_identifier()``.

Framework-Specific Handling
---------------------------

**Django CBVs** (``DisplayIDMixin``):
   All exceptions are converted to ``Http404``.

**Django REST Framework** (``DisplayIDMixin`` from ``contrib.rest_framework``):
   - ``ObjectNotFoundError`` → ``NotFound`` (404)
   - Other exceptions → ``ParseError`` (400)

**Django Admin** (``DisplayIDAdminSearchMixin``):
   Exceptions are silently caught and the search falls back to normal behavior.
