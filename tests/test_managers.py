"""Tests for managers module."""

import uuid

import pytest

from django_display_ids.encoding import encode_display_id
from django_display_ids.exceptions import (
    InvalidIdentifierError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
)

from .models import Invoice, Order, Product


@pytest.fixture
def invoice(db):
    """Create a test invoice."""
    return Invoice.objects.create(name="Test Invoice", slug="test-invoice")


@pytest.fixture
def product(db):
    """Create a test product."""
    return Product.objects.create(name="Test Product", handle="test-product")


@pytest.fixture
def order(db):
    """Create a test order (no display ID prefix)."""
    return Order.objects.create(name="Test Order", slug="test-order")


@pytest.mark.django_db
class TestGetByDisplayId:
    """Tests for get_by_display_id method."""

    def test_get_by_display_id(self, invoice):
        """Object is retrieved by display ID."""
        display_id = invoice.display_id
        result = Invoice.objects.get_by_display_id(display_id)
        assert result == invoice

    def test_display_id_not_found(self, invoice):
        """ObjectNotFoundError raised when display ID doesn't exist."""
        fake_display_id = encode_display_id("inv", uuid.uuid4())
        with pytest.raises(ObjectNotFoundError) as exc_info:
            Invoice.objects.get_by_display_id(fake_display_id)
        assert exc_info.value.model_name == "Invoice"

    def test_invalid_format(self, invoice):
        """InvalidIdentifierError raised for invalid display ID format."""
        with pytest.raises(InvalidIdentifierError):
            Invoice.objects.get_by_display_id("invalid-format")

    def test_wrong_prefix(self, invoice):
        """UnknownPrefixError raised when prefix doesn't match."""
        # Create a display ID with wrong prefix
        wrong_prefix_id = encode_display_id("prod", invoice.id)
        with pytest.raises(UnknownPrefixError) as exc_info:
            Invoice.objects.get_by_display_id(wrong_prefix_id)
        assert exc_info.value.actual == "prod"
        assert exc_info.value.expected == "inv"

    def test_explicit_prefix(self, invoice):
        """Explicit prefix parameter overrides model prefix."""
        # This would normally fail because of wrong prefix
        display_id = encode_display_id("custom", invoice.id)
        result = Invoice.objects.get_by_display_id(display_id, prefix="custom")
        assert result == invoice

    def test_model_without_prefix_raises_error(self, order):
        """MissingPrefixError raised for model without prefix."""
        fake_display_id = encode_display_id("ord", order.id)
        with pytest.raises(MissingPrefixError) as exc_info:
            Order.objects.get_by_display_id(fake_display_id)
        assert exc_info.value.model_name == "Order"

    def test_uuid_object(self, invoice):
        """Object is retrieved by UUID object directly."""
        result = Invoice.objects.get_by_display_id(invoice.id)
        assert result == invoice

    def test_uuid_object_not_found(self, invoice):
        """ObjectNotFoundError raised when UUID object doesn't exist."""
        with pytest.raises(ObjectNotFoundError):
            Invoice.objects.get_by_display_id(uuid.uuid4())


@pytest.mark.django_db
class TestGetByIdentifier:
    """Tests for get_by_identifier method."""

    def test_by_uuid(self, invoice):
        """Object is retrieved by UUID."""
        result = Invoice.objects.get_by_identifier(str(invoice.id))
        assert result == invoice

    def test_by_display_id(self, invoice):
        """Object is retrieved by display ID."""
        result = Invoice.objects.get_by_identifier(invoice.display_id)
        assert result == invoice

    def test_by_slug(self, invoice):
        """Object is retrieved by slug."""
        result = Invoice.objects.get_by_identifier(
            "test-invoice",
            strategies=("uuid", "display_id", "slug"),
        )
        assert result == invoice

    def test_not_found(self, invoice):
        """ObjectNotFoundError raised when identifier doesn't exist."""
        fake_uuid = uuid.uuid4()
        with pytest.raises(ObjectNotFoundError):
            Invoice.objects.get_by_identifier(str(fake_uuid))

    def test_invalid_identifier(self, invoice):
        """InvalidIdentifierError raised for invalid identifier."""
        with pytest.raises(InvalidIdentifierError):
            Invoice.objects.get_by_identifier(
                "invalid",
                strategies=("uuid",),  # Only UUID, won't match
            )

    def test_display_id_skipped_without_prefix(self, order):
        """display_id strategy is skipped for models without prefix."""
        # Order doesn't have display_id_prefix
        # UUID should still work
        result = Order.objects.get_by_identifier(str(order.id))
        assert result == order

    def test_display_id_only_without_prefix_raises_error(self, order):
        """InvalidIdentifierError when display_id is only strategy and no prefix."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            Order.objects.get_by_identifier(
                "anything",
                strategies=("display_id",),
            )
        assert "No strategies available" in str(exc_info.value)

    def test_custom_strategies(self, invoice):
        """Custom strategies are used."""
        # Only use slug strategy
        result = Invoice.objects.get_by_identifier(
            "test-invoice",
            strategies=("slug",),
        )
        assert result == invoice

    def test_explicit_prefix(self, invoice):
        """Explicit prefix parameter is used."""
        # Use a custom prefix
        display_id = encode_display_id("custom", invoice.id)
        result = Invoice.objects.get_by_identifier(
            display_id,
            strategies=("display_id",),
            prefix="custom",
        )
        assert result == invoice

    def test_uuid_object(self, invoice):
        """Object is retrieved by UUID object directly."""
        result = Invoice.objects.get_by_identifier(invoice.id)
        assert result == invoice

    def test_uuid_object_not_found(self, invoice):
        """ObjectNotFoundError raised when UUID object doesn't exist."""
        with pytest.raises(ObjectNotFoundError):
            Invoice.objects.get_by_identifier(uuid.uuid4())

    def test_uuid_object_skips_strategies(self, order):
        """UUID object works even for models without prefix."""
        result = Order.objects.get_by_identifier(order.id)
        assert result == order


@pytest.mark.django_db
class TestQuerySetChaining:
    """Tests for queryset method chaining."""

    def test_filter_then_get_by_display_id(self, db):
        """get_by_display_id works on filtered queryset."""
        invoice1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        result = Invoice.objects.filter(slug="invoice-1").get_by_display_id(
            invoice1.display_id
        )
        assert result == invoice1

    def test_filter_excludes_object(self, db):
        """ObjectNotFoundError when object excluded by filter."""
        Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        invoice2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        with pytest.raises(ObjectNotFoundError):
            Invoice.objects.filter(slug="invoice-1").get_by_display_id(
                invoice2.display_id
            )

    def test_filter_then_get_by_identifier(self, db):
        """get_by_identifier works on filtered queryset."""
        invoice1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        result = Invoice.objects.filter(slug="invoice-1").get_by_identifier(
            str(invoice1.id)
        )
        assert result == invoice1


@pytest.mark.django_db
class TestCustomFieldNames:
    """Tests for custom field name configuration."""

    def test_custom_uuid_field_in_manager(self, product):
        """Manager uses custom uuid_field from model."""
        result = Product.objects.get_by_identifier(str(product.uid))
        assert result == product

    def test_custom_slug_field_in_manager(self, product):
        """Manager uses custom slug_field from model."""
        result = Product.objects.get_by_identifier(
            "test-product",
            strategies=("slug",),
        )
        assert result == product

    def test_custom_fields_in_get_by_display_id(self, product):
        """get_by_display_id uses custom uuid_field."""
        result = Product.objects.get_by_display_id(product.display_id)
        assert result == product


@pytest.mark.django_db
class TestGetByIdentifiers:
    """Tests for get_by_identifiers batch lookup method."""

    def test_empty_list_returns_empty_queryset(self, db):
        """Empty input returns empty queryset."""
        result = Invoice.objects.get_by_identifiers([])
        assert result.count() == 0

    def test_by_display_ids(self, db):
        """Multiple objects retrieved by display IDs."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")
        Invoice.objects.create(name="Invoice 3", slug="invoice-3")

        result = Invoice.objects.get_by_identifiers(
            [
                inv1.display_id,
                inv2.display_id,
            ]
        )
        assert set(result) == {inv1, inv2}

    def test_by_uuids(self, db):
        """Multiple objects retrieved by UUIDs."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")
        Invoice.objects.create(name="Invoice 3", slug="invoice-3")

        result = Invoice.objects.get_by_identifiers(
            [
                str(inv1.id),
                str(inv2.id),
            ]
        )
        assert set(result) == {inv1, inv2}

    def test_by_slugs(self, db):
        """Multiple objects retrieved by slugs."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")
        Invoice.objects.create(name="Invoice 3", slug="invoice-3")

        result = Invoice.objects.get_by_identifiers(
            ["invoice-1", "invoice-2"],
            strategies=("uuid", "display_id", "slug"),
        )
        assert set(result) == {inv1, inv2}

    def test_mixed_identifier_types(self, db):
        """Handles mixed display ID, UUID, and slug in single query."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")
        inv3 = Invoice.objects.create(name="Invoice 3", slug="invoice-3")
        Invoice.objects.create(name="Invoice 4", slug="invoice-4")

        result = Invoice.objects.get_by_identifiers(
            [
                inv1.display_id,
                str(inv2.id),
                "invoice-3",
            ],
            strategies=("uuid", "display_id", "slug"),
        )
        assert set(result) == {inv1, inv2, inv3}

    def test_missing_identifiers_excluded(self, db):
        """Missing identifiers are silently excluded from results."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        fake_uuid = uuid.uuid4()

        result = Invoice.objects.get_by_identifiers(
            [
                inv1.display_id,
                str(fake_uuid),
            ]
        )
        assert list(result) == [inv1]

    def test_invalid_identifier_raises_error(self, db):
        """InvalidIdentifierError raised for unparseable identifier."""
        Invoice.objects.create(name="Invoice 1", slug="invoice-1")

        with pytest.raises(InvalidIdentifierError):
            Invoice.objects.get_by_identifiers(
                ["invalid-not-a-uuid"],
                strategies=("uuid",),
            )

    def test_works_with_filtered_queryset(self, db):
        """Batch lookup respects queryset filters."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        result = Invoice.objects.filter(slug="invoice-1").get_by_identifiers(
            [
                inv1.display_id,
                inv2.display_id,
            ]
        )
        assert list(result) == [inv1]

    def test_custom_prefix(self, db):
        """Explicit prefix parameter is used."""
        from django_display_ids.encoding import encode_display_id

        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        custom_display_id = encode_display_id("custom", inv1.id)

        result = Invoice.objects.get_by_identifiers(
            [custom_display_id],
            strategies=("display_id",),
            prefix="custom",
        )
        assert list(result) == [inv1]

    def test_custom_fields(self, db):
        """Works with models using custom field names."""
        prod1 = Product.objects.create(name="Product 1", handle="product-1")
        prod2 = Product.objects.create(name="Product 2", handle="product-2")

        result = Product.objects.get_by_identifiers(
            [
                prod1.display_id,
                str(prod2.uid),
            ]
        )
        assert set(result) == {prod1, prod2}

    def test_uuid_objects(self, db):
        """UUID objects are accepted alongside strings."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")
        Invoice.objects.create(name="Invoice 3", slug="invoice-3")

        result = Invoice.objects.get_by_identifiers(
            [
                inv1.id,  # UUID object
                inv2.id,  # UUID object
            ]
        )
        assert set(result) == {inv1, inv2}

    def test_mixed_uuid_objects_and_strings(self, db):
        """Handles mix of UUID objects, display IDs, and string UUIDs."""
        inv1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        inv2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")
        inv3 = Invoice.objects.create(name="Invoice 3", slug="invoice-3")

        result = Invoice.objects.get_by_identifiers(
            [
                inv1.id,  # UUID object
                inv2.display_id,  # display ID string
                str(inv3.id),  # UUID string
            ]
        )
        assert set(result) == {inv1, inv2, inv3}
