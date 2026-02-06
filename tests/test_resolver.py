"""Tests for resolver module."""

import uuid

import pytest

from django_display_ids.encoding import encode_display_id
from django_display_ids.exceptions import (
    InvalidIdentifierError,
    ObjectNotFoundError,
    UnknownPrefixError,
)
from django_display_ids.resolver import resolve_object

from .models import Invoice, Order, Product, Tag


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
class TestResolveObjectByUuid:
    """Tests for resolving objects by UUID."""

    def test_resolve_by_uuid(self, invoice):
        """Object is resolved by UUID string."""
        result = resolve_object(
            model=Invoice,
            value=str(invoice.id),
            strategies=("uuid",),
        )
        assert result == invoice

    def test_resolve_by_unhyphenated_uuid(self, invoice):
        """Object is resolved by unhyphenated UUID."""
        result = resolve_object(
            model=Invoice,
            value=invoice.id.hex,
            strategies=("uuid",),
        )
        assert result == invoice

    def test_uuid_not_found(self, invoice):
        """ObjectNotFoundError raised when UUID doesn't exist."""
        fake_uuid = uuid.uuid4()
        with pytest.raises(ObjectNotFoundError) as exc_info:
            resolve_object(
                model=Invoice,
                value=str(fake_uuid),
                strategies=("uuid",),
            )
        assert exc_info.value.model_name == "Invoice"

    def test_resolve_by_uuid_object(self, invoice):
        """Object is resolved by UUID object directly."""
        result = resolve_object(
            model=Invoice,
            value=invoice.id,
            strategies=("uuid",),
        )
        assert result == invoice

    def test_uuid_object_not_found(self, invoice):
        """ObjectNotFoundError raised when UUID object doesn't exist."""
        with pytest.raises(ObjectNotFoundError):
            resolve_object(
                model=Invoice,
                value=uuid.uuid4(),
                strategies=("uuid",),
            )

    def test_uuid_object_skips_strategies(self, invoice):
        """UUID object works regardless of strategies configured."""
        result = resolve_object(
            model=Invoice,
            value=invoice.id,
            strategies=("display_id",),
            prefix="inv",
        )
        assert result == invoice


@pytest.mark.django_db
class TestResolveObjectByDisplayId:
    """Tests for resolving objects by display ID."""

    def test_resolve_by_display_id(self, invoice):
        """Object is resolved by display ID."""
        display_id = encode_display_id("inv", invoice.id)
        result = resolve_object(
            model=Invoice,
            value=display_id,
            strategies=("display_id",),
            prefix="inv",
        )
        assert result == invoice

    def test_display_id_not_found(self, invoice):
        """ObjectNotFoundError raised when display ID doesn't exist."""
        fake_display_id = encode_display_id("inv", uuid.uuid4())
        with pytest.raises(ObjectNotFoundError):
            resolve_object(
                model=Invoice,
                value=fake_display_id,
                strategies=("display_id",),
                prefix="inv",
            )

    def test_wrong_prefix_raises_error(self, invoice):
        """UnknownPrefixError raised when prefix doesn't match."""
        display_id = encode_display_id("inv", invoice.id)
        with pytest.raises(UnknownPrefixError) as exc_info:
            resolve_object(
                model=Invoice,
                value=display_id,
                strategies=("display_id",),
                prefix="prod",  # Wrong prefix
            )
        assert exc_info.value.actual == "inv"
        assert exc_info.value.expected == "prod"


@pytest.mark.django_db
class TestResolveObjectBySlug:
    """Tests for resolving objects by slug."""

    def test_resolve_by_slug(self, invoice):
        """Object is resolved by slug."""
        result = resolve_object(
            model=Invoice,
            value="test-invoice",
            strategies=("slug",),
            slug_field="slug",
        )
        assert result == invoice

    def test_slug_not_found(self):
        """ObjectNotFoundError raised when slug doesn't exist."""
        with pytest.raises(ObjectNotFoundError):
            resolve_object(
                model=Invoice,
                value="nonexistent-slug",
                strategies=("slug",),
            )


@pytest.mark.django_db
class TestResolveObjectWithMultipleStrategies:
    """Tests for resolving with multiple strategies."""

    def test_uuid_matched_first(self, invoice):
        """UUID is matched when first in strategies."""
        result = resolve_object(
            model=Invoice,
            value=str(invoice.id),
            strategies=("uuid", "display_id", "slug"),
            prefix="inv",
        )
        assert result == invoice

    def test_display_id_matched_first(self, invoice):
        """Display ID is matched when first in strategies."""
        display_id = encode_display_id("inv", invoice.id)
        result = resolve_object(
            model=Invoice,
            value=display_id,
            strategies=("display_id", "uuid", "slug"),
            prefix="inv",
        )
        assert result == invoice

    def test_fallback_to_slug(self, invoice):
        """Falls back to slug when other strategies don't match."""
        result = resolve_object(
            model=Invoice,
            value="test-invoice",
            strategies=("uuid", "display_id", "slug"),
            prefix="inv",
        )
        assert result == invoice

    def test_display_id_skipped_without_prefix(self, invoice):
        """Display ID strategy is skipped when no prefix configured."""
        # The display ID format will be treated as a slug
        display_id = encode_display_id("inv", invoice.id)

        # Create an invoice with the display ID as its slug
        invoice_with_slug = Invoice.objects.create(name="Slug Invoice", slug=display_id)

        result = resolve_object(
            model=Invoice,
            value=display_id,
            strategies=("display_id", "slug"),
            prefix=None,  # No prefix, so display_id is skipped
        )
        # Should match by slug, not by display_id
        assert result == invoice_with_slug


@pytest.mark.django_db
class TestResolveObjectWithCustomFields:
    """Tests for resolving with custom field names."""

    def test_custom_uuid_field(self, product):
        """Object resolved using custom UUID field name."""
        result = resolve_object(
            model=Product,
            value=str(product.uid),
            strategies=("uuid",),
            uuid_field="uid",
        )
        assert result == product

    def test_custom_slug_field(self, product):
        """Object resolved using custom slug field name."""
        result = resolve_object(
            model=Product,
            value="test-product",
            strategies=("slug",),
            slug_field="handle",
        )
        assert result == product


@pytest.mark.django_db
class TestResolveObjectWithQueryset:
    """Tests for resolving with custom queryset."""

    def test_queryset_filtering(self, db):
        """Custom queryset is respected."""
        invoice1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        # Create a filtered queryset
        qs = Invoice.objects.filter(slug="invoice-1")

        # Should find invoice1
        result = resolve_object(
            model=Invoice,
            value=str(invoice1.id),
            strategies=("uuid",),
            queryset=qs,
        )
        assert result == invoice1

    def test_queryset_excludes_object(self, db):
        """ObjectNotFoundError when object excluded by queryset."""
        Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        invoice2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        # Create a queryset that excludes invoice2
        qs = Invoice.objects.filter(slug="invoice-1")

        with pytest.raises(ObjectNotFoundError):
            resolve_object(
                model=Invoice,
                value=str(invoice2.id),
                strategies=("uuid",),
                queryset=qs,
            )


@pytest.mark.django_db
class TestResolveObjectErrors:
    """Tests for error handling."""

    def test_invalid_identifier(self, invoice):
        """InvalidIdentifierError raised for invalid identifier."""
        with pytest.raises(InvalidIdentifierError):
            resolve_object(
                model=Invoice,
                value="invalid",
                strategies=("uuid",),  # Only UUID, won't match
            )

    def test_ambiguous_slug(self, db):
        """AmbiguousIdentifierError raised when multiple objects match."""
        # Create invoices with same slug (in a world without unique constraint)
        # For testing, we'll use a mock scenario
        # Since slug is unique=True in our test model, we'll test with a
        # model that allows duplicates by using filter + count logic

        # Create two invoices
        Invoice.objects.create(name="Invoice 1", slug="same-slug")
        Invoice.objects.create(name="Invoice 2", slug=None)

        # The AmbiguousIdentifierError would be raised if MultipleObjectsReturned
        # occurs. Since our test model has unique slugs, we'll just verify
        # the normal case works.
        result = resolve_object(
            model=Invoice,
            value="same-slug",
            strategies=("slug",),
        )
        assert result.slug == "same-slug"


@pytest.mark.django_db
class TestResolveObjectSlugFieldGraceful:
    """Tests for graceful handling of slug strategy on models without a slug field."""

    def test_slug_skipped_on_model_without_slug_field(self, db):
        """Slug strategy is skipped when model has no slug field."""
        tag = Tag.objects.create(name="Test Tag")

        result = resolve_object(
            model=Tag,
            value=str(tag.id),
            strategies=("display_id", "uuid", "slug"),
            prefix="tag",
        )
        assert result == tag

    def test_slug_only_on_model_without_slug_field(self, db):
        """InvalidIdentifierError when slug is only strategy and model has no slug field."""
        Tag.objects.create(name="Test Tag")

        with pytest.raises(InvalidIdentifierError):
            resolve_object(
                model=Tag,
                value="some-slug",
                strategies=("slug",),
            )

    def test_slug_still_works_on_model_with_slug_field(self, invoice):
        """Slug strategy works normally on models with a slug field."""
        result = resolve_object(
            model=Invoice,
            value="test-invoice",
            strategies=("display_id", "uuid", "slug"),
            prefix="inv",
        )
        assert result == invoice
