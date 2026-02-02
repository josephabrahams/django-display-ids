"""Tests for Django REST Framework view mixins and serializer fields."""

import uuid

import pytest
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from django_display_ids.contrib.rest_framework import (
    DisplayIDField,
    DisplayIDLookupMixin,
)
from django_display_ids.encoding import encode_display_id

from .models import Invoice, Order, Product

# Skip all tests if DRF is not installed
pytest.importorskip("rest_framework")


class InvoiceAPIView(DisplayIDLookupMixin, APIView):
    """Test API view for Invoice model."""

    lookup_url_kwarg = "id"
    display_id_prefix = "inv"

    def get_queryset(self):
        return Invoice.objects.all()


class ProductAPIView(DisplayIDLookupMixin, APIView):
    """Test API view for Product model with custom fields."""

    lookup_url_kwarg = "id"
    display_id_prefix = "prod"
    uuid_field = "uid"
    slug_field = "handle"
    lookup_strategies = ("display_id", "uuid", "slug")

    def get_queryset(self):
        return Product.objects.all()


class NoPrefixAPIView(DisplayIDLookupMixin, APIView):
    """Test API view without display_id_prefix."""

    lookup_url_kwarg = "id"
    display_id_prefix = None  # Explicitly disable model's prefix

    def get_queryset(self):
        return Invoice.objects.all()


class ModelPrefixFallbackAPIView(DisplayIDLookupMixin, APIView):
    """Test API view that inherits prefix from model."""

    lookup_url_kwarg = "id"
    # display_id_prefix not set - should fall back to model's "inv"

    def get_queryset(self):
        return Invoice.objects.all()


@pytest.fixture
def rf():
    """API request factory."""
    return APIRequestFactory()


@pytest.fixture
def invoice(db):
    """Create a test invoice."""
    return Invoice.objects.create(name="Test Invoice", slug="test-invoice")


@pytest.fixture
def product(db):
    """Create a test product."""
    return Product.objects.create(name="Test Product", handle="test-product")


@pytest.mark.django_db
class TestDisplayIDLookupMixin:
    """Tests for DisplayIDLookupMixin."""

    def test_get_object_by_uuid(self, rf, invoice):
        """get_object works with UUID."""
        view = InvoiceAPIView()
        view.kwargs = {"id": str(invoice.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_get_object_by_display_id(self, rf, invoice):
        """get_object works with display ID."""
        view = InvoiceAPIView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_get_object_not_found(self, rf, invoice):
        """NotFound raised when object not found."""
        view = InvoiceAPIView()
        view.kwargs = {"id": str(uuid.uuid4())}
        view.request = rf.get("/")

        with pytest.raises(NotFound):
            view.get_object()

    def test_get_object_invalid_identifier(self, rf, invoice):
        """ParseError raised for invalid identifier."""
        view = InvoiceAPIView()
        view.kwargs = {"id": "invalid"}
        view.request = rf.get("/")

        with pytest.raises(ParseError):
            view.get_object()

    def test_get_object_wrong_prefix(self, rf, invoice):
        """ParseError raised for wrong prefix."""
        view = InvoiceAPIView()
        # Use prod prefix instead of inv
        wrong_display_id = encode_display_id("prod", invoice.id)
        view.kwargs = {"id": wrong_display_id}
        view.request = rf.get("/")

        with pytest.raises(ParseError):
            view.get_object()

    def test_missing_lookup_param(self, rf, invoice):
        """ParseError raised when lookup param is missing."""
        view = InvoiceAPIView()
        view.kwargs = {}  # Missing 'id'
        view.request = rf.get("/")

        with pytest.raises(ParseError, match="Missing URL parameter"):
            view.get_object()


@pytest.mark.django_db
class TestCustomFieldConfiguration:
    """Tests for custom field configuration."""

    def test_custom_uuid_field(self, rf, product):
        """View uses custom uuid_field."""
        view = ProductAPIView()
        view.kwargs = {"id": str(product.uid)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == product

    def test_custom_slug_field(self, rf, product):
        """View uses custom slug_field."""
        view = ProductAPIView()
        view.kwargs = {"id": "test-product"}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == product


@pytest.mark.django_db
class TestQuerysetFiltering:
    """Tests for queryset filtering."""

    def test_get_queryset_filtering(self, rf, db):
        """Custom get_queryset is respected."""
        invoice1 = Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        class FilteredInvoiceView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = "inv"

            def get_queryset(self):
                return Invoice.objects.filter(slug="invoice-1")

        view = FilteredInvoiceView()
        view.kwargs = {"id": str(invoice1.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice1

    def test_filtered_queryset_excludes_object(self, rf, db):
        """NotFound when object excluded by queryset filter."""
        Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        invoice2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        class FilteredInvoiceView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = "inv"

            def get_queryset(self):
                return Invoice.objects.filter(slug="invoice-1")

        view = FilteredInvoiceView()
        view.kwargs = {"id": str(invoice2.id)}
        view.request = rf.get("/")

        with pytest.raises(NotFound):
            view.get_object()


@pytest.mark.django_db
class TestNoPrefixBehavior:
    """Tests for views without display_id_prefix."""

    def test_uuid_still_works(self, rf, invoice):
        """UUID lookup still works without prefix."""
        view = NoPrefixAPIView()
        view.kwargs = {"id": str(invoice.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_display_id_skipped(self, rf, invoice):
        """Display ID is treated as invalid without prefix."""
        view = NoPrefixAPIView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        # Should raise ParseError because display_id strategy is skipped
        # and the display ID format doesn't match UUID
        with pytest.raises(ParseError):
            view.get_object()


@pytest.mark.django_db
class TestObjectPermissions:
    """Tests for object-level permissions."""

    def test_check_object_permissions_called(self, rf, invoice):
        """check_object_permissions is called on retrieved object."""
        permissions_checked = []

        class PermissionCheckView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = "inv"

            def get_queryset(self):
                return Invoice.objects.all()

            def check_object_permissions(self, request, obj):
                permissions_checked.append(obj)

        view = PermissionCheckView()
        view.kwargs = {"id": str(invoice.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice
        assert permissions_checked == [invoice]


@pytest.mark.django_db
class TestModelPrefixFallback:
    """Tests for automatic prefix inheritance from model."""

    def test_inherits_prefix_from_model(self, rf, invoice):
        """View without display_id_prefix uses model's prefix."""
        view = ModelPrefixFallbackAPIView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_view_prefix_overrides_model(self, rf, invoice):
        """View's explicit prefix takes precedence over model's."""
        # InvoiceAPIView has display_id_prefix = "inv" explicitly set
        view = InvoiceAPIView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_none_disables_model_prefix(self, rf, invoice):
        """Setting display_id_prefix = None disables model's prefix."""
        view = NoPrefixAPIView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        # Should raise ParseError because display_id strategy is skipped
        with pytest.raises(ParseError):
            view.get_object()


class TestPrefixValidation:
    """Tests for prefix validation on views."""

    def test_empty_string_raises_error(self, rf):
        """Empty string prefix raises ValueError."""

        class EmptyPrefixView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = ""

            def get_queryset(self):
                return Invoice.objects.all()

        view = EmptyPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()

    def test_invalid_prefix_raises_error(self, rf):
        """Invalid prefix format raises ValueError."""

        class InvalidPrefixView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = "Invalid123"

            def get_queryset(self):
                return Invoice.objects.all()

        view = InvalidPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()

    def test_too_long_prefix_raises_error(self, rf):
        """Prefix longer than 16 chars raises ValueError."""

        class LongPrefixView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = "waytoolongprefix123"

            def get_queryset(self):
                return Invoice.objects.all()

        view = LongPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()


# =============================================================================
# DisplayIDField Tests
# =============================================================================


class InvoiceSerializer(serializers.Serializer):
    """Test serializer with DisplayIDField."""

    id = serializers.UUIDField(read_only=True)
    display_id = DisplayIDField()
    name = serializers.CharField()


class ProductSerializer(serializers.Serializer):
    """Test serializer with custom prefix override."""

    id = serializers.UUIDField(source="uid", read_only=True)
    display_id = DisplayIDField(prefix="item")  # Override model's "prod" prefix
    name = serializers.CharField()


class OrderSerializer(serializers.Serializer):
    """Test serializer for model without display_id_prefix."""

    id = serializers.UUIDField(read_only=True)
    display_id = DisplayIDField()
    name = serializers.CharField()


@pytest.fixture
def order(db):
    """Create a test order (no display_id_prefix)."""
    return Order.objects.create(name="Test Order", slug="test-order")


@pytest.mark.django_db
class TestDisplayIDField:
    """Tests for DisplayIDField serializer field."""

    def test_returns_display_id_from_model(self, invoice):
        serializer = InvoiceSerializer(invoice)
        data = serializer.data

        assert data["display_id"] == invoice.display_id
        assert data["display_id"].startswith("inv_")

    def test_raises_error_for_model_without_prefix(self, order):
        serializer = OrderSerializer(order)

        with pytest.raises(ValueError, match="requires a prefix"):
            _ = serializer.data

    def test_prefix_override(self, product):
        serializer = ProductSerializer(product)
        data = serializer.data

        # Should use "item" prefix from field, not "prod" from model
        assert data["display_id"].startswith("item_")

        # Verify the display_id decodes to the correct UUID
        # Product uses uuid_field = "uid", so the field should read from that
        from django_display_ids.encoding import decode_display_id

        prefix, decoded_uuid = decode_display_id(data["display_id"])
        assert prefix == "item"
        assert decoded_uuid == product.uid

    def test_field_is_read_only(self, invoice):
        serializer = InvoiceSerializer(
            invoice, data={"display_id": "should_be_ignored", "name": "New Name"}
        )
        # Field should be read-only, input ignored
        assert serializer.fields["display_id"].read_only is True


class InvoiceModelSerializer(serializers.ModelSerializer):
    """Test ModelSerializer with DisplayIDField - has Meta.model for schema generation."""

    display_id = DisplayIDField()

    class Meta:
        model = Invoice
        fields = ("id", "display_id", "name")


@pytest.mark.django_db
class TestDisplayIDFieldSchema:
    """Tests for DisplayIDField OpenAPI schema generation via drf-spectacular extension."""

    def test_extension_generates_schema_with_model_prefix(self, invoice):
        """Extension generates proper schema when serializer has Meta.model."""
        pytest.importorskip("drf_spectacular")
        from django_display_ids.contrib.drf_spectacular import DisplayIDFieldExtension

        serializer = InvoiceModelSerializer(invoice)
        field = serializer.fields["display_id"]

        # Create extension instance targeting our field
        ext = DisplayIDFieldExtension(target=field)
        schema = ext.map_serializer_field(None, "response")

        assert schema["type"] == "string"
        assert "pattern" in schema
        # Model has display_id_prefix = "inv"
        assert schema["example"].startswith("inv_")

    def test_extension_generates_schema_with_prefix_override(self, product):
        """Extension uses field's prefix override."""
        pytest.importorskip("drf_spectacular")
        from django_display_ids.contrib.drf_spectacular import DisplayIDFieldExtension

        serializer = ProductSerializer(product)
        field = serializer.fields["display_id"]

        ext = DisplayIDFieldExtension(target=field)
        schema = ext.map_serializer_field(None, "response")

        # Field has prefix="item" override
        assert schema["example"].startswith("item_")

    def test_extension_generates_generic_schema_without_prefix(self):
        """Extension generates generic schema when no prefix available."""
        pytest.importorskip("drf_spectacular")
        from django_display_ids.contrib.drf_spectacular import DisplayIDFieldExtension

        field = DisplayIDField()
        # Simulate binding without a parent that has Meta.model
        field._prefix_override = None
        field.parent = None

        ext = DisplayIDFieldExtension(target=field)
        schema = ext.map_serializer_field(None, "response")

        assert schema["type"] == "string"
        assert "type_" in schema["example"]  # Generic example

    def test_plain_serializer_gets_generic_schema(self, invoice):
        """Plain Serializer without Meta.model gets generic schema."""
        pytest.importorskip("drf_spectacular")
        from django_display_ids.contrib.drf_spectacular import DisplayIDFieldExtension

        # InvoiceSerializer is a plain Serializer, not ModelSerializer
        serializer = InvoiceSerializer(invoice)
        field = serializer.fields["display_id"]

        ext = DisplayIDFieldExtension(target=field)
        schema = ext.map_serializer_field(None, "response")

        # No Meta.model, so generic schema
        assert schema["type"] == "string"
        assert "type_" in schema["example"]


# =============================================================================
# ID Parameter Description Tests
# =============================================================================


class TestIdParamDescription:
    """Tests for id_param_description function."""

    def test_function_default(self):
        from django_display_ids.contrib.drf_spectacular import id_param_description

        result = id_param_description("user")
        assert result == "Identifier: display_id (user_xxx) or UUID"

    def test_function_without_uuid(self):
        from django_display_ids.contrib.drf_spectacular import id_param_description

        result = id_param_description("user", with_uuid=False)
        assert result == "Identifier: display_id (user_xxx)"

    def test_function_with_slug(self):
        from django_display_ids.contrib.drf_spectacular import id_param_description

        result = id_param_description("app", with_slug=True)
        assert result == "Identifier: display_id (app_xxx), UUID, or slug"

    def test_function_without_uuid_with_slug(self):
        from django_display_ids.contrib.drf_spectacular import id_param_description

        result = id_param_description("app", with_uuid=False, with_slug=True)
        assert result == "Identifier: display_id (app_xxx) or slug"

    def test_various_prefixes(self):
        from django_display_ids.contrib.drf_spectacular import id_param_description

        assert "inv_xxx" in id_param_description("inv")
        assert "product_xxx" in id_param_description("product")
        assert "a_xxx" in id_param_description("a")
