"""Tests for exceptions module."""

import pytest
from django.core.exceptions import (
    ImproperlyConfigured,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)

from django_display_ids.exceptions import (
    AmbiguousIdentifierError,
    DisplayIDLookupError,
    InvalidIdentifierError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
)


@pytest.mark.parametrize(
    ("error", "django_base"),
    [
        (InvalidIdentifierError("x"), ValueError),
        (UnknownPrefixError("x", actual="a"), ValueError),
        (MissingPrefixError(), ImproperlyConfigured),
        (ObjectNotFoundError("x"), ObjectDoesNotExist),
        (AmbiguousIdentifierError("x", count=2), MultipleObjectsReturned),
    ],
    ids=lambda v: type(v).__name__ if isinstance(v, Exception) else v.__name__,
)
def test_caught_by_library_and_django_base(error, django_base):
    """Existing `except` clauses for the Django or Python base keep working."""
    with pytest.raises(DisplayIDLookupError):
        raise error
    with pytest.raises(django_base):
        raise error


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (InvalidIdentifierError("x"), "Invalid identifier: 'x'"),
        (InvalidIdentifierError("x", "custom"), "custom"),
        (
            UnknownPrefixError("inv_a", actual="inv", expected="prod"),
            "Unknown prefix 'inv' in 'inv_a', expected 'prod'",
        ),
        (UnknownPrefixError("inv_a", actual="inv"), "Unknown prefix 'inv' in 'inv_a'"),
        (
            MissingPrefixError(model_name="Invoice"),
            "Cannot lookup by display ID: Invoice does not have a "
            "display_id_prefix configured",
        ),
        (MissingPrefixError(), "Cannot lookup by display ID: no prefix configured"),
        (
            ObjectNotFoundError("inv_a", model_name="Invoice"),
            "Invoice not found for identifier: 'inv_a'",
        ),
        (ObjectNotFoundError("inv_a"), "Object not found for identifier: 'inv_a'"),
        (
            AmbiguousIdentifierError("my-slug", count=3),
            "Ambiguous identifier 'my-slug': matched 3 objects",
        ),
    ],
)
def test_message(error, message):
    assert str(error) == message


def test_attributes():
    assert InvalidIdentifierError("x", "custom").value == "x"
    assert InvalidIdentifierError("x", "custom").message == "custom"

    error = UnknownPrefixError("inv_a", actual="inv", expected="prod")
    assert (error.value, error.actual, error.expected) == ("inv_a", "inv", "prod")

    assert MissingPrefixError(model_name="Invoice").model_name == "Invoice"
    assert MissingPrefixError().model_name is None

    error = ObjectNotFoundError("inv_a", model_name="Invoice")
    assert (error.value, error.model_name) == ("inv_a", "Invoice")

    error = AmbiguousIdentifierError("my-slug", count=3)
    assert (error.value, error.count) == ("my-slug", 3)
