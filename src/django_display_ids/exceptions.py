"""Typed exceptions for identifier lookup errors.

All exceptions inherit from both ``DisplayIDLookupError`` and a standard
Django/Python exception, so they integrate naturally with existing error
handling patterns::

    # Catch with library-specific base
    except DisplayIDLookupError: ...

    # Or catch with standard Django/Python exceptions
    except ObjectDoesNotExist: ...   # catches ObjectNotFoundError
    except ValueError: ...           # catches InvalidIdentifierError, UnknownPrefixError
    except ImproperlyConfigured: ... # catches MissingPrefixError
"""

from __future__ import annotations

from django.core.exceptions import (
    ImproperlyConfigured,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)

__all__ = [
    "AmbiguousIdentifierError",
    "DisplayIDLookupError",
    "InvalidIdentifierError",
    "MissingPrefixError",
    "ObjectNotFoundError",
    "UnknownPrefixError",
]


class DisplayIDLookupError(Exception):
    """Base exception for all lookup errors."""

    pass


class InvalidIdentifierError(DisplayIDLookupError, ValueError):
    """Raised when an identifier has an invalid format.

    This indicates the identifier string cannot be parsed as any
    of the supported formats (UUID, display ID, or slug).

    Inherits from ``ValueError`` because it represents bad input — the
    caller provided a value that isn't a valid identifier.
    """

    def __init__(self, value: str, message: str | None = None) -> None:
        self.value = value
        self.message = message or f"Invalid identifier: {value!r}"
        super().__init__(self.message)


class UnknownPrefixError(DisplayIDLookupError, ValueError):
    """Raised when a display ID has an unexpected prefix.

    This occurs when prefix enforcement is enabled and the
    display ID's prefix doesn't match the expected value.

    Inherits from ``ValueError`` because it represents bad input — the
    caller provided a display ID with the wrong prefix.
    """

    def __init__(self, value: str, actual: str, expected: str | None = None) -> None:
        self.value = value
        self.actual = actual
        self.expected = expected
        if expected:
            message = f"Unknown prefix {actual!r} in {value!r}, expected {expected!r}"
        else:
            message = f"Unknown prefix {actual!r} in {value!r}"
        super().__init__(message)


class MissingPrefixError(DisplayIDLookupError, ImproperlyConfigured):
    """Raised when a display ID lookup is attempted without a prefix.

    This occurs when calling get_by_display_id() on a model that
    doesn't have display_id_prefix configured.

    Inherits from ``ImproperlyConfigured`` because it represents a
    configuration problem — the model is missing a required setting.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        if model_name:
            message = (
                f"Cannot lookup by display ID: {model_name} does not have "
                "a display_id_prefix configured"
            )
        else:
            message = "Cannot lookup by display ID: no prefix configured"
        super().__init__(message)


class ObjectNotFoundError(DisplayIDLookupError, ObjectDoesNotExist):
    """Raised when no object matches the identifier.

    This indicates the identifier was valid but no matching
    database record exists.

    Inherits from ``ObjectDoesNotExist`` so it integrates with Django's
    built-in error handling (e.g., ``get_object_or_404``).
    """

    def __init__(self, value: str, model_name: str | None = None) -> None:
        self.value = value
        self.model_name = model_name
        if model_name:
            message = f"{model_name} not found for identifier: {value!r}"
        else:
            message = f"Object not found for identifier: {value!r}"
        super().__init__(message)


class AmbiguousIdentifierError(DisplayIDLookupError, MultipleObjectsReturned):
    """Raised when an identifier matches multiple objects.

    This can occur with slug lookups if slugs are not unique,
    or in edge cases with identifier collisions.

    Inherits from ``MultipleObjectsReturned`` because the semantics
    are identical — a lookup that expected one result found many.
    """

    def __init__(self, value: str, count: int) -> None:
        self.value = value
        self.count = count
        super().__init__(f"Ambiguous identifier {value!r}: matched {count} objects")
