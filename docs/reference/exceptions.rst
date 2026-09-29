Exceptions
==========

``resolve_object()`` and the parsing functions raise these. Each one subclasses
``DisplayIDLookupError`` and the Django or Python exception it corresponds to,
so an existing ``except`` clause for the standard exception still catches it:

.. list-table::
   :header-rows: 1

   * - Exception
     - Also a
     - Raised when
   * - ``InvalidIdentifierError``
     - ``ValueError``
     - No strategy can read the value
   * - ``UnknownPrefixError``
     - ``ValueError``
     - A display ID has another model's prefix
   * - ``ObjectNotFoundError``
     - ``ObjectDoesNotExist``
     - Nothing matches
   * - ``AmbiguousIdentifierError``
     - ``MultipleObjectsReturned``
     - A slug matches more than one row
   * - ``MissingPrefixError``
     - ``ImproperlyConfigured``
     - A lookup needs a prefix and the model has none

For example:

.. code-block:: python

   from django.core.exceptions import ObjectDoesNotExist
   from django_display_ids import UnknownPrefixError, resolve_object

   try:
       invoice = resolve_object(Invoice, value)
   except UnknownPrefixError as e:
       print(f"Expected {e.expected}_..., got {e.actual}_...")
   except ObjectDoesNotExist:  # also catches ObjectNotFoundError
       invoice = None

The exceptions carry the details as attributes: ``value`` on all of them except
``MissingPrefixError``; ``actual`` and ``expected`` on ``UnknownPrefixError``;
``model_name`` on ``ObjectNotFoundError`` and ``MissingPrefixError``; and
``count`` on ``AmbiguousIdentifierError``.

Where they surface
------------------

Not every entry point raises these directly:

Manager methods (``get_by_identifier()`` and friends)
   Raise ``Model.DoesNotExist`` for anything that doesn't match, like
   ``QuerySet.get()``. ``get_by_identifiers()`` leaves non-matches out, like
   ``filter()``.

Django and DRF view mixins
   Return a 404 for anything that doesn't match. A slug that matches more than
   one row raises the model's ``MultipleObjectsReturned``, as Django's and
   DRF's ``get_object()`` do.

Admin search
   An identifier that doesn't parse or has the wrong prefix just adds no match
   to the results.

``DisplayIDRelatedField``
   Reports non-matches as a ``does_not_exist`` validation error.

In all of them, configuration errors (``MissingPrefixError`` and
``ImproperlyConfigured``) are raised as they are, because they mean the code
needs fixing rather than the input.
