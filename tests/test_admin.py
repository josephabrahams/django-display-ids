"""Tests for Django admin integration."""

import uuid  # Used for generating fake display IDs

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from django_display_ids import DisplayIDAdminSearchMixin, encode_display_id

from .models import Invoice, Product


class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
    """Test admin for Invoice model."""

    list_display = ("id", "name")
    search_fields = ("name",)


class ProductAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
    """Test admin for Product model with custom uuid_field."""

    list_display = ("uid", "name")
    search_fields = ("name",)


@pytest.fixture
def admin_site():
    """Create an admin site for testing."""
    return AdminSite()


@pytest.fixture
def invoice_admin(admin_site):
    """Create InvoiceAdmin instance."""
    return InvoiceAdmin(Invoice, admin_site)


@pytest.fixture
def product_admin(admin_site):
    """Create ProductAdmin instance."""
    return ProductAdmin(Product, admin_site)


@pytest.fixture
def request_factory():
    """Create a request factory."""
    return RequestFactory()


@pytest.mark.django_db
class TestDisplayIDAdminSearchMixin:
    """Tests for DisplayIDAdminSearchMixin."""

    def test_search_by_display_id(self, invoice_admin, request_factory):
        """Should find invoice by display_id search."""
        invoice = Invoice.objects.create(name="Test Invoice")
        display_id = encode_display_id("inv", invoice.id)

        request = request_factory.get("/admin/tests/invoice/", {"q": display_id})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(request, queryset, display_id)

        assert invoice in result_qs
        assert result_qs.count() == 1

    def test_search_by_name(self, invoice_admin, request_factory):
        """Should still support regular search fields."""
        invoice = Invoice.objects.create(name="Unique Name Here")

        request = request_factory.get("/admin/tests/invoice/", {"q": "Unique"})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(request, queryset, "Unique")

        assert invoice in result_qs

    def test_search_invalid_display_id(self, invoice_admin, request_factory):
        """Should not error on invalid display_id format."""
        Invoice.objects.create(name="Test Invoice")

        request = request_factory.get("/admin/tests/invoice/", {"q": "invalid_xxx"})
        queryset = Invoice.objects.all()

        # Should not raise, just return empty or original results
        result_qs, _ = invoice_admin.get_search_results(
            request, queryset, "invalid_xxx"
        )

        # No match expected
        assert result_qs.count() == 0

    def test_search_custom_uuid_field(self, product_admin, request_factory):
        """Should work with custom uuid_field on model."""
        product = Product.objects.create(name="Test Product")
        display_id = encode_display_id("prod", product.uid)

        request = request_factory.get("/admin/tests/product/", {"q": display_id})
        queryset = Product.objects.all()

        result_qs, _ = product_admin.get_search_results(request, queryset, display_id)

        assert product in result_qs
        assert result_qs.count() == 1

    def test_search_nonexistent_display_id(self, invoice_admin, request_factory):
        """Should return empty when display_id doesn't match any record."""
        Invoice.objects.create(name="Test Invoice")
        fake_display_id = encode_display_id("inv", uuid.uuid4())

        request = request_factory.get("/admin/tests/invoice/", {"q": fake_display_id})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(
            request, queryset, fake_display_id
        )

        assert result_qs.count() == 0

    def test_search_combines_with_text_search(self, invoice_admin, request_factory):
        """Display ID search should combine with regular search results."""
        invoice1 = Invoice.objects.create(name="First Invoice")
        invoice2 = Invoice.objects.create(name="Second Invoice")
        display_id = encode_display_id("inv", invoice1.id)

        request = request_factory.get("/admin/tests/invoice/", {"q": display_id})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(request, queryset, display_id)

        # Should find invoice1 via display_id
        assert invoice1 in result_qs
        # Should not find invoice2
        assert invoice2 not in result_qs

    def test_search_by_raw_uuid(self, invoice_admin, request_factory):
        """Should find invoice by raw UUID search."""
        invoice = Invoice.objects.create(name="Test Invoice")
        raw_uuid = str(invoice.id)

        request = request_factory.get("/admin/tests/invoice/", {"q": raw_uuid})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(request, queryset, raw_uuid)

        assert invoice in result_qs
        assert result_qs.count() == 1

    def test_search_by_raw_uuid_no_hyphens(self, invoice_admin, request_factory):
        """Should find invoice by raw UUID without hyphens."""
        invoice = Invoice.objects.create(name="Test Invoice")
        raw_uuid = invoice.id.hex

        request = request_factory.get("/admin/tests/invoice/", {"q": raw_uuid})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(request, queryset, raw_uuid)

        assert invoice in result_qs
        assert result_qs.count() == 1

    def test_search_by_raw_uuid_custom_field(self, product_admin, request_factory):
        """Should find product by raw UUID with custom uuid_field."""
        product = Product.objects.create(name="Test Product")
        raw_uuid = str(product.uid)

        request = request_factory.get("/admin/tests/product/", {"q": raw_uuid})
        queryset = Product.objects.all()

        result_qs, _ = product_admin.get_search_results(request, queryset, raw_uuid)

        assert product in result_qs
        assert result_qs.count() == 1


class TestParseIdentifier:
    """Tests for _parse_identifier static method."""

    def test_parse_display_id(self):
        """Should parse a display ID and return the UUID."""
        uid = uuid.uuid4()
        display_id = encode_display_id("inv", uid)
        assert DisplayIDAdminSearchMixin._parse_identifier(display_id) == uid

    def test_parse_raw_uuid(self):
        """Should parse a raw UUID with hyphens."""
        uid = uuid.uuid4()
        assert DisplayIDAdminSearchMixin._parse_identifier(str(uid)) == uid

    def test_parse_raw_uuid_no_hyphens(self):
        """Should parse a raw UUID without hyphens."""
        uid = uuid.uuid4()
        assert DisplayIDAdminSearchMixin._parse_identifier(uid.hex) == uid

    def test_parse_plain_text(self):
        """Should return None for plain text."""
        assert DisplayIDAdminSearchMixin._parse_identifier("hello world") is None

    def test_parse_invalid_display_id(self):
        """Should return None for invalid display ID."""
        assert DisplayIDAdminSearchMixin._parse_identifier("inv_notvalid") is None

    def test_parse_empty_string(self):
        """Should return None for empty string."""
        assert DisplayIDAdminSearchMixin._parse_identifier("") is None
