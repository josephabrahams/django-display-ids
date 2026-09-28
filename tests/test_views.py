"""Tests for Django view mixins."""

import uuid

import pytest
from django.core.exceptions import ImproperlyConfigured, MultipleObjectsReturned
from django.http import Http404
from django.test import RequestFactory
from django.views.generic import DetailView

from django_display_ids.encoding import encode_display_id
from django_display_ids.views import DisplayIDMixin

from .models import Invoice, Product, Tag


class InvoiceDetailView(DisplayIDMixin, DetailView):
    """Test view for Invoice model."""

    model = Invoice
    lookup_url_kwarg = "id"
    display_id_prefix = "inv"


class ProductDetailView(DisplayIDMixin, DetailView):
    """Test view for Product model with custom fields."""

    model = Product
    lookup_url_kwarg = "id"
    display_id_prefix = "prod"
    uuid_field = "uid"
    slug_field = "handle"
    lookup_strategies = ("display_id", "uuid", "slug")


class TagDetailView(DisplayIDMixin, DetailView):
    """Test view for Tag model (no slug field)."""

    model = Tag
    lookup_url_kwarg = "id"
    display_id_prefix = "tag"


class NoPrefixView(DisplayIDMixin, DetailView):
    """Test view without display_id_prefix."""

    model = Invoice
    lookup_url_kwarg = "id"
    lookup_strategies = ("uuid", "slug")  # No display_id strategy


class ModelPrefixFallbackView(DisplayIDMixin, DetailView):
    """Test view that inherits prefix from model."""

    model = Invoice
    lookup_url_kwarg = "id"
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
class TestDisplayIDMixin:
    """Tests for DisplayIDMixin."""

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

    def test_missing_lookup_url_kwarg(self, rf, invoice):
        """A missing URL parameter is a URLconf bug, not a 404."""
        view = InvoiceDetailView()
        view.kwargs = {}  # Missing 'id'
        view.request = rf.get("/")

        with pytest.raises(AttributeError, match="'id' URL parameter"):
            view.get_object()

    def test_get_object_padded_identifier(self, rf, invoice):
        """Surrounding whitespace is ignored."""
        view = InvoiceDetailView()
        view.kwargs = {"id": f" {invoice.display_id} "}
        view.request = rf.get("/")

        assert view.get_object() == invoice


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

        class FilteredInvoiceView(DisplayIDMixin, DetailView):
            model = Invoice
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
        """Http404 when object excluded by queryset filter."""
        Invoice.objects.create(name="Invoice 1", slug="invoice-1")
        invoice2 = Invoice.objects.create(name="Invoice 2", slug="invoice-2")

        class FilteredInvoiceView(DisplayIDMixin, DetailView):
            model = Invoice
            lookup_url_kwarg = "id"
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

    def test_missing_model_and_queryset_raises_error(self, rf):
        """Django's own ImproperlyConfigured is raised with neither set."""

        class NoModelView(DisplayIDMixin, DetailView):
            lookup_url_kwarg = "id"

        view = NoModelView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ImproperlyConfigured):
            view.get_object()

    def test_queryset_without_model(self, rf, invoice):
        """The model is taken from the queryset when not set on the view."""

        class QuerysetOnlyView(DisplayIDMixin, DetailView):
            queryset = Invoice.objects.all()
            lookup_url_kwarg = "id"

        view = QuerysetOnlyView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        assert view.get_object() == invoice


@pytest.mark.django_db
class TestAmbiguousSlug:
    """Duplicate slugs raise like Django's get_object() instead of 404ing."""

    def test_ambiguous_slug_raises(self, rf):
        from .models import Order

        # name isn't unique, so use it as the slug field to get duplicates
        Order.objects.create(name="dup")
        Order.objects.create(name="dup")

        class OrderView(DisplayIDMixin, DetailView):
            model = Order
            lookup_url_kwarg = "id"
            slug_field = "name"

        view = OrderView()
        view.kwargs = {"id": "dup"}
        view.request = rf.get("/")

        with pytest.raises(MultipleObjectsReturned):
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

    def test_no_display_id_strategy_skips_prefix(self, rf, invoice):
        """Omitting display_id from strategies skips prefix matching."""
        view = NoPrefixView()
        view.kwargs = {"id": invoice.display_id}
        view.request = rf.get("/")

        # Should raise 404 because display_id strategy is not in strategies
        with pytest.raises(Http404):
            view.get_object()


class TestPrefixValidation:
    """Tests for prefix validation on views."""

    def test_empty_string_raises_error(self, rf):
        """Empty string prefix raises ValueError."""

        class EmptyPrefixView(DisplayIDMixin, DetailView):
            model = Invoice
            lookup_url_kwarg = "id"
            display_id_prefix = ""

        view = EmptyPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()

    def test_invalid_prefix_raises_error(self, rf):
        """Invalid prefix format raises ValueError."""

        class InvalidPrefixView(DisplayIDMixin, DetailView):
            model = Invoice
            lookup_url_kwarg = "id"
            display_id_prefix = "Invalid123"

        view = InvalidPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()

    def test_too_long_prefix_raises_error(self, rf):
        """Prefix longer than 16 chars raises ValueError."""

        class LongPrefixView(DisplayIDMixin, DetailView):
            model = Invoice
            lookup_url_kwarg = "id"
            display_id_prefix = "waytoolongprefix123"

        view = LongPrefixView()
        view.kwargs = {"id": "test"}
        view.request = rf.get("/")

        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            view.get_object()


@pytest.mark.django_db
class TestSlugFieldGracefulInViews:
    """Tests for graceful slug handling in views for models without a slug field."""

    def test_uuid_works_on_model_without_slug_field(self, rf, db):
        """UUID lookup works on models without a slug field."""
        tag = Tag.objects.create(name="Test Tag")

        view = TagDetailView()
        view.kwargs = {"id": str(tag.id)}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == tag

    def test_display_id_works_on_model_without_slug_field(self, rf, db):
        """Display ID lookup works on models without a slug field."""
        tag = Tag.objects.create(name="Test Tag")

        view = TagDetailView()
        view.kwargs = {"id": tag.display_id}
        view.request = rf.get("/")

        obj = view.get_object()
        assert obj == tag

    def test_slug_string_raises_404_on_model_without_slug_field(self, rf, db):
        """Slug string raises 404 on models without a slug field."""
        Tag.objects.create(name="Test Tag")

        view = TagDetailView()
        view.kwargs = {"id": "some-slug"}
        view.request = rf.get("/")

        with pytest.raises(Http404):
            view.get_object()


class TestLookupParamRenamed:
    """lookup_param was renamed to lookup_url_kwarg in 0.8."""

    def test_old_name_fails_at_class_definition(self):
        with pytest.raises(TypeError, match="renamed to lookup_url_kwarg"):

            class OldStyleView(DisplayIDMixin, DetailView):
                model = Invoice
                lookup_param = "id"

    def test_new_name_is_used(self, rf, db):
        invoice = Invoice.objects.create(name="x")

        class NewStyleView(DisplayIDMixin, DetailView):
            model = Invoice
            lookup_url_kwarg = "invoice_id"

        view = NewStyleView()
        view.kwargs = {"invoice_id": invoice.display_id}
        view.request = rf.get("/")
        assert view.get_object() == invoice
