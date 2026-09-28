"""Tests for resolve_object() and the shared lookup behind every entry point.

Which identifier forms are accepted or rejected, and how each option
overrides the model, is covered for every entry point in
test_consistency.py. These tests cover the resolver's own error types,
UUID objects, settings and querysets.
"""

import uuid

import pytest

from django_display_ids.encoding import encode_display_id
from django_display_ids.exceptions import (
    AmbiguousIdentifierError,
    InvalidIdentifierError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
)
from django_display_ids.resolver import _Lookup, resolve_object

from .models import Invoice, Order, Product

pytestmark = pytest.mark.django_db


class TestErrors:
    """resolve_object() raises the library's typed errors."""

    def test_not_found(self, invoice):
        with pytest.raises(ObjectNotFoundError) as exc_info:
            resolve_object(Invoice, str(uuid.uuid4()))
        assert exc_info.value.model_name == "Invoice"

    def test_unparseable(self, invoice):
        with pytest.raises(InvalidIdentifierError):
            resolve_object(Invoice, "invalid", strategies=("uuid",))

    def test_wrong_prefix(self, invoice):
        with pytest.raises(UnknownPrefixError) as exc_info:
            resolve_object(Invoice, invoice.display_id, prefix="prod")
        assert (exc_info.value.actual, exc_info.value.expected) == ("inv", "prod")

    def test_ambiguous_slug(self):
        # name isn't unique, so use it as the slug field to get duplicates
        Order.objects.create(name="dup")
        Order.objects.create(name="dup")
        with pytest.raises(AmbiguousIdentifierError) as exc_info:
            resolve_object(Order, "dup", strategies=("slug",), slug_field="name")
        assert exc_info.value.count == 2

    def test_queryset_for_another_model(self, invoice):
        with pytest.raises(TypeError, match="queryset must be for Invoice"):
            resolve_object(Invoice, invoice.display_id, queryset=Order.objects.all())

    def test_neither_display_id_nor_slug_usable(self):
        """With nothing left to try, the missing prefix is reported."""
        with pytest.raises(MissingPrefixError):
            resolve_object(
                Order, "x", strategies=("display_id", "slug"), slug_field="missing"
            )


class TestUUIDObjects:
    def test_found(self, invoice, product):
        assert resolve_object(Invoice, invoice.id) == invoice
        assert resolve_object(Product, product.uid) == product  # uid, not pk

    def test_not_found(self, invoice):
        with pytest.raises(ObjectNotFoundError):
            resolve_object(Invoice, uuid.uuid4())

    def test_skip_strategies(self, invoice):
        """A UUID object is already parsed, so strategies don't apply."""
        assert resolve_object(Invoice, invoice.id, strategies=("slug",)) == invoice

    def test_configuration_errors_still_raise(self, order):
        """Strategies that can never work for the model are a configuration
        error whatever the value, so a UUID object doesn't hide the mistake."""
        with pytest.raises(MissingPrefixError):
            resolve_object(Order, order.id, strategies=("display_id",))


class TestSettings:
    def test_uuid_field(self, invoice, settings):
        """Invoice sets no uuid_field, so UUID_FIELD is used.

        Pointing it at the slug column makes the lookup miss, which shows the
        setting was read.
        """
        settings.DISPLAY_IDS = {"UUID_FIELD": "slug"}
        with pytest.raises(ObjectNotFoundError):
            resolve_object(Invoice, str(invoice.id), strategies=("uuid",))

    def test_slug_field(self, invoice, settings):
        settings.DISPLAY_IDS = {"SLUG_FIELD": "name"}
        assert resolve_object(Invoice, "Test Invoice", strategies=("slug",)) == invoice


def test_queryset(invoice):
    other = Invoice.objects.create(name="Other", slug="other")
    queryset = Invoice.objects.filter(slug="test-invoice")
    assert resolve_object(Invoice, invoice.display_id, queryset=queryset) == invoice
    with pytest.raises(ObjectNotFoundError):
        resolve_object(Invoice, other.display_id, queryset=queryset)


class TestLookup:
    """The shared lookup object every entry point uses."""

    def test_build_and_encode_round_trip(self):
        lookup = _Lookup.for_model(Product)
        value = uuid.uuid4()
        display_id = lookup.encode(value)
        assert display_id == encode_display_id("prod", value)
        assert lookup.build(display_id) == {"uid": value}

    def test_require_prefix(self):
        assert _Lookup.for_model(Invoice).require_prefix() == "inv"
        lookup = _Lookup.for_model(Order, strategies=("uuid",))
        with pytest.raises(MissingPrefixError, match="Order"):
            lookup.require_prefix()
        with pytest.raises(MissingPrefixError):
            lookup.encode(uuid.uuid4())
