"""Tests for Django view mixins."""

import uuid

import pytest
from django.http import Http404
from django.test import RequestFactory
from django.views.generic import DetailView

from django_display_ids.encoding import encode_display_id
from django_display_ids.views import DisplayIDObjectMixin

from .models import Invoice, Product


class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
    """Test view for Invoice model."""

    model = Invoice
    lookup_param = "id"
    display_id_prefix = "inv"


class ProductDetailView(DisplayIDObjectMixin, DetailView):
    """Test view for Product model with custom fields."""

    model = Product
    lookup_param = "id"
    display_id_prefix = "prod"
    uuid_field = "uid"
    slug_field = "handle"
    lookup_strategies = ("display_id", "uuid", "slug")


class NoPrefixView(DisplayIDObjectMixin, DetailView):
    """Test view without display_id_prefix."""

    model = Invoice
    lookup_param = "id"
    display_id_prefix = None  # Explicitly disable model's prefix


class ModelPrefixFallbackView(DisplayIDObjectMixin, DetailView):
    """Test view that inherits prefix from model."""

    model = Invoice
    lookup_param = "id"
    # display_id_prefix not set - should fall back to model's "inv"


@pytest.fixture
def rf():
    """Request factory."""
    return RequestFactory()


@pytest.fixture
def invoice(db):
    """Create a test invoice."""
    return Invoice.objects.create(name="Test Invoice", slug="test-invoice")


@pytest.fixture
def product(db):
    """Create a test product."""
    return Product.objects.create(name="Test Product", handle="test-product")


@pytest.mark.django_db
class TestDisplayIDObjectMixin:
    """Tests for DisplayIDObjectMixin."""

    def test_get_object_by_uuid(self, rf, invoice):
        """get_object works with UUID."""
        view = InvoiceDetailView()
        view.kwargs = {"id": str(invoice.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_get_object_by_display_id(self, rf, invoice):
        """get_object works with display ID."""
        view = InvoiceDetailView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_get_object_not_found(self, rf, invoice):
        """Http404 raised when object not found."""
        view = InvoiceDetailView()
        view.kwargs = {"id": str(uuid.uuid4())}
        view.request = rf.get("/")

        with pytest.raises(Http404):
            view.get_object()

    def test_get_object_invalid_identifier(self, rf, invoice):
        """Http404 raised for invalid identifier."""
        view = InvoiceDetailView()
        view.kwargs = {"id": "invalid"}
        view.request = rf.get("/")

        with pytest.raises(Http404):
            view.get_object()

    def test_get_object_wrong_prefix(self, rf, invoice):
        """Http404 raised for wrong prefix."""
        view = InvoiceDetailView()
        # Use prod prefix instead of inv
        wrong_display_id = encode_display_id("prod", invoice.id)
        view.kwargs = {"id": wrong_display_id}
        view.request = rf.get("/")

        with pytest.raises(Http404):
            view.get_object()

    def test_missing_lookup_param(self, rf, invoice):
        """Http404 raised when lookup param is missing."""
        view = InvoiceDetailView()
        view.kwargs = {}  # Missing 'id'
        view.request = rf.get("/")

        with pytest.raises(Http404, match="Missing URL parameter"):
            view.get_object()


@pytest.mark.django_db
class TestCustomFieldConfiguration:
    """Tests for custom field configuration."""

    def test_custom_uuid_field(self, rf, product):
        """View uses custom uuid_field."""
        view = ProductDetailView()
        view.kwargs = {"id": str(product.uid)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == product

    def test_custom_slug_field(self, rf, product):
        """View uses custom slug_field."""
        view = ProductDetailView()
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

        class FilteredInvoiceView(DisplayIDObjectMixin, DetailView):
            model = Invoice
            lookup_param = "id"
            display_id_prefix = "inv"

            def get_queryset(self):
                return Invoice.objects.filter(slug="invoice-1")

        view = FilteredInvoiceView()
        view.kwargs = {"id": str(invoice1.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice1

    def test_filtered_queryset_excludes_object(self, rf, db):
        """Http404 when object excluded by queryset filter."""
        Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        invoice2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        class FilteredInvoiceView(DisplayIDObjectMixin, DetailView):
            model = Invoice
            lookup_param = "id"
            display_id_prefix = "inv"

            def get_queryset(self):
                return Invoice.objects.filter(slug="invoice-1")

        view = FilteredInvoiceView()
        view.kwargs = {"id": str(invoice2.id)}
        view.request = rf.get("/")

        with pytest.raises(Http404):
            view.get_object()


@pytest.mark.django_db
class TestNoPrefixBehavior:
    """Tests for views without display_id_prefix."""

    def test_uuid_still_works(self, rf, invoice):
        """UUID lookup still works without prefix."""
        view = NoPrefixView()
        view.kwargs = {"id": str(invoice.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_display_id_skipped(self, rf, invoice):
        """Display ID is treated as invalid without prefix."""
        view = NoPrefixView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        # Should raise 404 because display_id strategy is skipped
        # and the display ID format doesn't match UUID
        with pytest.raises(Http404):
            view.get_object()


@pytest.mark.django_db
class TestModelAttribute:
    """Tests for model attribute requirement."""

    def test_missing_model_raises_error(self, rf):
        """AttributeError raised when model is not set."""

        class NoModelView(DisplayIDObjectMixin, DetailView):
            lookup_param = "id"
            # model not set (intentionally omitted)

        view = NoModelView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(AttributeError, match="must define 'model'"):
            view.get_object()


@pytest.mark.django_db
class TestModelPrefixFallback:
    """Tests for automatic prefix inheritance from model."""

    def test_inherits_prefix_from_model(self, rf, invoice):
        """View without display_id_prefix uses model's prefix."""
        view = ModelPrefixFallbackView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_view_prefix_overrides_model(self, rf, invoice):
        """View's explicit prefix takes precedence over model's."""
        # InvoiceDetailView has display_id_prefix = "inv" explicitly set
        view = InvoiceDetailView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == invoice

    def test_none_disables_model_prefix(self, rf, invoice):
        """Setting display_id_prefix = None disables model's prefix."""
        view = NoPrefixView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        # Should raise 404 because display_id strategy is skipped
        with pytest.raises(Http404):
            view.get_object()


class TestPrefixValidation:
    """Tests for prefix validation on views."""

    def test_empty_string_raises_error(self, rf):
        """Empty string prefix raises ValueError."""

        class EmptyPrefixView(DisplayIDObjectMixin, DetailView):
            model = Invoice
            lookup_param = "id"
            display_id_prefix = ""

        view = EmptyPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()

    def test_invalid_prefix_raises_error(self, rf):
        """Invalid prefix format raises ValueError."""

        class InvalidPrefixView(DisplayIDObjectMixin, DetailView):
            model = Invoice
            lookup_param = "id"
            display_id_prefix = "Invalid123"

        view = InvalidPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()

    def test_too_long_prefix_raises_error(self, rf):
        """Prefix longer than 16 chars raises ValueError."""

        class LongPrefixView(DisplayIDObjectMixin, DetailView):
            model = Invoice
            lookup_param = "id"
            display_id_prefix = "waytoolongprefix123"

        view = LongPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()
