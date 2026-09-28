"""Tests for Django admin integration."""

import uuid  # Used for generating fake display IDs

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from django_display_ids import DisplayIDAdminSearchMixin, encode_display_id

from .models import Invoice, Order, Product


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

    def test_search_by_display_id_with_whitespace(self, invoice_admin, request_factory):
        """Should find invoice when the pasted display ID has stray whitespace."""
        invoice = Invoice.objects.create(name="Test Invoice")
        padded = f"  {encode_display_id('inv', invoice.id)}\n"

        request = request_factory.get("/admin/tests/invoice/", {"q": padded})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(request, queryset, padded)

        assert invoice in result_qs
        assert result_qs.count() == 1

    def test_search_by_multi_word_name(self, invoice_admin, request_factory):
        """Interior whitespace must still split into per-word text search."""
        invoice = Invoice.objects.create(name="Unique Name Here")
        Invoice.objects.create(name="Unique Other")

        request = request_factory.get("/admin/tests/invoice/", {"q": "Unique Here"})
        queryset = Invoice.objects.all()

        result_qs, _ = invoice_admin.get_search_results(
            request, queryset, "Unique Here"
        )

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

    def test_search_respects_queryset_scoping(self, invoice_admin, request_factory):
        """UUID search should not return rows excluded from the input queryset.

        Ensures the mixin filters against the passed-in queryset (which may be
        tenant-scoped) rather than the default manager.
        """
        included = Invoice.objects.create(name="Included")
        excluded = Invoice.objects.create(name="Excluded")

        # Search for the *excluded* invoice's display ID, but pass a queryset
        # that only contains the *included* invoice — simulating tenant scoping.
        display_id = encode_display_id("inv", excluded.id)
        scoped_qs = Invoice.objects.filter(pk=included.pk)

        request = request_factory.get("/admin/tests/invoice/", {"q": display_id})
        result_qs, _ = invoice_admin.get_search_results(request, scoped_qs, display_id)

        assert excluded not in result_qs
        assert result_qs.count() == 0

    def test_search_by_raw_uuid_respects_queryset_scoping(
        self, invoice_admin, request_factory
    ):
        """Raw UUID search should not return rows excluded from the input queryset."""
        included = Invoice.objects.create(name="Included")
        excluded = Invoice.objects.create(name="Excluded")

        raw_uuid = str(excluded.id)
        scoped_qs = Invoice.objects.filter(pk=included.pk)

        request = request_factory.get("/admin/tests/invoice/", {"q": raw_uuid})
        result_qs, _ = invoice_admin.get_search_results(request, scoped_qs, raw_uuid)

        assert excluded not in result_qs
        assert result_qs.count() == 0


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

    def test_parse_display_id_with_surrounding_whitespace(self):
        """Should strip whitespace around a pasted display ID."""
        uid = uuid.uuid4()
        display_id = encode_display_id("inv", uid)
        assert DisplayIDAdminSearchMixin._parse_identifier(f"  {display_id}\n") == uid

    def test_parse_raw_uuid_with_surrounding_whitespace(self):
        """Should strip whitespace around a pasted raw UUID."""
        uid = uuid.uuid4()
        assert DisplayIDAdminSearchMixin._parse_identifier(f"  {uid}\n") == uid

    def test_parse_whitespace_only(self):
        """Should return None for a whitespace-only search term."""
        assert DisplayIDAdminSearchMixin._parse_identifier("   ") is None

    def test_parse_display_id_with_interior_whitespace(self):
        """Should not match a display ID broken up by interior whitespace."""
        uid = uuid.uuid4()
        display_id = encode_display_id("inv", uid)
        assert DisplayIDAdminSearchMixin._parse_identifier(f"inv_ {display_id}") is None

    def test_model_prefix_must_match(self):
        """With model=, display IDs must use that model's prefix."""
        uid = uuid.uuid4()
        parse = DisplayIDAdminSearchMixin._parse_identifier
        assert parse(encode_display_id("inv", uid), model=Invoice) == uid
        assert parse(encode_display_id("prod", uid), model=Invoice) is None
        assert parse(str(uid), model=Invoice) == uid

    def test_model_without_prefix_matches_uuids_only(self):
        """With a model that has no prefix, only raw UUIDs match."""
        uid = uuid.uuid4()
        parse = DisplayIDAdminSearchMixin._parse_identifier
        assert parse(encode_display_id("inv", uid), model=Order) is None
        assert parse(str(uid), model=Order) == uid


@pytest.mark.django_db
class TestAdminStrategies:
    """Admin search uses the same strategies and overrides as the views."""

    def _search(self, admin_class, term):
        qs, _ = admin_class(Invoice, AdminSite()).get_search_results(
            None, Invoice.objects.all(), term
        )
        return list(qs)

    def test_lookup_strategies_attribute(self):
        invoice = Invoice.objects.create(name="x", slug="my-slug")

        class UUIDOnlyAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            search_fields = ("name",)
            lookup_strategies = ("uuid",)

        assert self._search(UUIDOnlyAdmin, str(invoice.id)) == [invoice]
        assert self._search(UUIDOnlyAdmin, invoice.display_id) == []
        assert self._search(UUIDOnlyAdmin, "my-slug") == []

    def test_display_id_prefix_attribute(self):
        invoice = Invoice.objects.create(name="x")

        class CustomPrefixAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            search_fields = ("name",)
            display_id_prefix = "bill"

        assert self._search(CustomPrefixAdmin, invoice.display_id) == []
        bill_id = encode_display_id("bill", invoice.id)
        assert self._search(CustomPrefixAdmin, bill_id) == [invoice]

    def test_slug_field_attribute(self):
        invoice = Invoice.objects.create(name="Exact Name")

        class NameAsSlugAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            # A search field that never matches, so only the slug lookup can
            search_fields = ("slug",)
            slug_field = "name"

        assert self._search(NameAsSlugAdmin, "Exact Name") == [invoice]
        assert self._search(NameAsSlugAdmin, "Exact") == []

    def test_empty_search_adds_nothing(self):
        """Loading the changelist (empty search) doesn't add a slug match."""
        Invoice.objects.create(name="x", slug=None)

        class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            search_fields = ("name",)

        # Empty search returns the full queryset, same as plain ModelAdmin
        assert len(self._search(InvoiceAdmin, "")) == 1
        assert len(self._search(InvoiceAdmin, "   ")) == 1
