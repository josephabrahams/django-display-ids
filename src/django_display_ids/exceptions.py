"""Typed exceptions for identifier lookup errors."""

from __future__ import annotations

__all__ = [
    "AmbiguousIdentifierError",
    "InvalidIdentifierError",
    "LookupError",
    "MissingPrefixError",
    "ObjectNotFoundError",
    "UnknownPrefixError",
]


class LookupError(Exception):
    """Base exception for all lookup errors."""

    pass


class InvalidIdentifierError(LookupError):
    """Raised when an identifier has an invalid format.

    This indicates the identifier string cannot be parsed as any
    of the supported formats (UUID, display ID, or slug).
    """

    def __init__(self, value: str, message: str | None = None) -> None:
        self.value = value
        self.message = message or f"Invalid identifier: {value!r}"
        super().__init__(self.message)


class UnknownPrefixError(LookupError):
    """Raised when a display ID has an unexpected prefix.

    This occurs when prefix enforcement is enabled and the
    display ID's prefix doesn't match the expected value.
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


class MissingPrefixError(LookupError):
    """Raised when a display ID lookup is attempted without a prefix.

    This occurs when calling get_by_display_id() on a model that
    doesn't have display_id_prefix configured.
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


class ObjectNotFoundError(LookupError):
    """Raised when no object matches the identifier.

    This indicates the identifier was valid but no matching
    database record exists.
    """

    def __init__(self, value: str, model_name: str | None = None) -> None:
        self.value = value
        self.model_name = model_name
        if model_name:
            message = f"{model_name} not found for identifier: {value!r}"
        else:
            message = f"Object not found for identifier: {value!r}"
        super().__init__(message)


class AmbiguousIdentifierError(LookupError):
    """Raised when an identifier matches multiple objects.

    This can occur with slug lookups if slugs are not unique,
    or in edge cases with identifier collisions.
    """

    def __init__(self, value: str, count: int) -> None:
        self.value = value
        self.count = count
        super().__init__(f"Ambiguous identifier {value!r}: matched {count} objects")
