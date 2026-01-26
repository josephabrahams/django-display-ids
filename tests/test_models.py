"""Tests for models module."""

import uuid

import pytest

from django_display_ids.encoding import encode_display_id
from django_display_ids.models import DisplayIDMixin, get_model_for_prefix

from .models import Invoice, Order, Product


@pytest.mark.django_db
class TestDisplayIDMixin:
    """Tests for DisplayIDMixin."""

    def test_display_id_property(self):
        """display_id property returns correct format."""
        invoice = Invoice.objects.create(name="Test Invoice")
        display_id = invoice.display_id

        assert display_id.startswith("inv_")
        assert len(display_id) == 3 + 1 + 22  # prefix + _ + base62

    def test_display_id_matches_encode_function(self):
        """display_id property matches encode_display_id function."""
        invoice = Invoice.objects.create(name="Test Invoice")
        expected = encode_display_id("inv", invoice.id)
        assert invoice.display_id == expected

    def test_display_id_deterministic(self):
        """display_id returns same value each time."""
        invoice = Invoice.objects.create(name="Test Invoice")
        assert invoice.display_id == invoice.display_id

    def test_different_instances_have_different_ids(self):
        """Different instances have different display IDs."""
        invoice1 = Invoice.objects.create(name="Invoice 1")
        invoice2 = Invoice.objects.create(name="Invoice 2")
        assert invoice1.display_id != invoice2.display_id

    def test_get_display_id_prefix_classmethod(self):
        """get_display_id_prefix returns correct prefix."""
        assert Invoice.get_display_id_prefix() == "inv"
        assert Product.get_display_id_prefix() == "prod"

    def test_get_display_id_prefix_not_implemented(self):
        """get_display_id_prefix raises error for models without prefix."""
        # Order doesn't use DisplayIDMixin
        assert not hasattr(Order, "get_display_id_prefix")


@pytest.mark.django_db
class TestCustomFieldNames:
    """Tests for custom field name configuration."""

    def test_custom_uuid_field(self):
        """Custom uuid_field is used for display_id generation."""
        product = Product.objects.create(name="Test Product")
        # Product uses 'uid' field, not 'id'
        expected = encode_display_id("prod", product.uid)
        assert product.display_id == expected

    def test_get_uuid_field(self):
        """_get_uuid_field returns custom field name."""
        assert Invoice._get_uuid_field() == "id"
        assert Product._get_uuid_field() == "uid"

    def test_get_slug_field(self):
        """_get_slug_field returns custom field name."""
        assert Invoice._get_slug_field() == "slug"
        assert Product._get_slug_field() == "handle"


class TestPrefixRegistry:
    """Tests for prefix collision detection."""

    def test_get_model_for_prefix(self):
        """get_model_for_prefix returns registered model name."""
        assert get_model_for_prefix("inv") == "Invoice"
        assert get_model_for_prefix("prod") == "Product"

    def test_get_model_for_unregistered_prefix(self):
        """get_model_for_prefix returns None for unregistered prefix."""
        assert get_model_for_prefix("unknown") is None

    def test_prefix_collision_raises_error(self):
        """Defining duplicate prefix raises ValueError at class definition."""
        with pytest.raises(ValueError, match="already used"):
            # This should fail at class definition time
            class DuplicateInvoice(DisplayIDMixin):
                display_id_prefix = "inv"  # Already used by Invoice

                class Meta:
                    app_label = "tests"

    def test_abstract_models_are_registered(self):
        """Abstract models with prefixes are registered.

        This is intentional - registering abstract models ensures collision
        detection works across the inheritance hierarchy. If an abstract base
        claims a prefix, concrete subclasses that don't override it will
        inherit it, and other models cannot reuse it.
        """

        # Define an abstract model
        class AbstractModel(DisplayIDMixin):
            display_id_prefix = "abstract"

            class Meta:
                abstract = True
                app_label = "tests"

        # Abstract models are registered for collision detection
        assert get_model_for_prefix("abstract") == "AbstractModel"

    def test_empty_prefix_raises_error(self):
        """Empty string prefix raises ValueError at class definition."""
        with pytest.raises(ValueError, match="1-16 lowercase letters"):

            class EmptyPrefixModel(DisplayIDMixin):
                display_id_prefix = ""

                class Meta:
                    app_label = "tests"

    def test_invalid_prefix_raises_error(self):
        """Invalid prefix format raises ValueError at class definition."""
        with pytest.raises(ValueError, match="1-16 lowercase letters"):

            class InvalidPrefixModel(DisplayIDMixin):
                display_id_prefix = "Invalid123"

                class Meta:
                    app_label = "tests"

    def test_too_long_prefix_raises_error(self):
        """Prefix longer than 16 chars raises ValueError at class definition."""
        with pytest.raises(ValueError, match="1-16 lowercase letters"):

            class LongPrefixModel(DisplayIDMixin):
                display_id_prefix = "waytoolongprefix123"

                class Meta:
                    app_label = "tests"


@pytest.mark.django_db
class TestDisplayIDMixinWithDatabase:
    """Tests requiring database access."""

    def test_display_id_after_save(self):
        """display_id is available after saving."""
        invoice = Invoice(name="Test Invoice")
        # Before save, id might be set by default
        invoice.save()
        assert invoice.display_id is not None
        assert invoice.display_id.startswith("inv_")

    def test_display_id_with_explicit_uuid(self):
        """display_id works with explicitly set UUID."""
        explicit_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        invoice = Invoice.objects.create(id=explicit_uuid, name="Test Invoice")

        expected = encode_display_id("inv", explicit_uuid)
        assert invoice.display_id == expected

    def test_display_id_survives_refresh(self):
        """display_id is consistent after refresh_from_db."""
        invoice = Invoice.objects.create(name="Test Invoice")
        original_display_id = invoice.display_id

        invoice.refresh_from_db()
        assert invoice.display_id == original_display_id
