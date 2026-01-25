"""Tests for Django REST Framework view mixins."""

import uuid

import pytest
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from django_display_ids.contrib.rest_framework import DisplayIDLookupMixin
from django_display_ids.encoding import encode_display_id

from .models import Invoice, Product

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
    # No display_id_prefix set

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
