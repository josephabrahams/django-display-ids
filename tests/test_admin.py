"""Tests for the admin search mixin.

Which identifier forms are accepted or rejected, and how each option (prefix,
strategies, fields) overrides the model, is covered for every entry
point in test_consistency.py. These tests cover admin-specific behavior.
"""

import uuid
from typing import ClassVar

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite

from django_display_ids import (
    DisplayIDAdminSearchMixin,
    DisplayIDType,
    encode_display_id,
)

from .models import Invoice, LineItem, Order, Product


class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
    search_fields = ("name",)


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def search(admin_site):
    """Run an admin search and return the matching rows as a list."""

    def _search(term, admin_class=InvoiceAdmin, model=Invoice, queryset=None):
        model_admin = admin_class(model, admin_site)
        if queryset is None:
            queryset = model.objects.all()
        results, _ = model_admin.get_search_results(None, queryset, term)
        return list(results)

    return _search


@pytest.mark.django_db
class TestSearch:
    def test_text_search_still_works(self, search):
        """Interior whitespace still splits into per-word text search."""
        invoice = Invoice.objects.create(name="Unique Name Here")
        Invoice.objects.create(name="Unique Other")
        assert search("Unique Here") == [invoice]

    def test_combined_with_text_search(self, search):
        """An ID match is added to the text-search results, not substituted."""
        by_id = Invoice.objects.create(name="First")
        by_name = Invoice.objects.create(name=str(by_id.id))
        assert {*search(str(by_id.id))} == {by_id, by_name}

    def test_unparseable_term_is_not_an_error(self, search):
        Invoice.objects.create(name="Test Invoice")
        assert search("invalid_xxx") == []

    def test_empty_search_returns_everything(self, search):
        """Loading the changelist (empty search) doesn't add a slug match."""
        Invoice.objects.create(name="x", slug=None)
        assert len(search("")) == 1
        assert len(search("   ")) == 1

    @pytest.mark.parametrize("form", ["display_id", "uuid"])
    def test_respects_queryset_scoping(self, search, form):
        """The ID match is filtered from the queryset passed in (e.g. per tenant),
        not the default manager."""
        included = Invoice.objects.create(name="Included")
        excluded = Invoice.objects.create(name="Excluded")
        term = excluded.display_id if form == "display_id" else str(excluded.id)
        assert search(term, queryset=Invoice.objects.filter(pk=included.pk)) == []


class LineItemAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
    search_fields = ("name",)
    display_id_search_fields: ClassVar = {
        "invoice_id": Invoice,
        "products__uid": Product,
    }


# A display ID with no model, stored in a UUID column (here LineItem.uid)
Reference = DisplayIDType("ref")


class TypedLineItemAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
    search_fields = ("name",)
    display_id_search_fields: ClassVar = {"uid": Reference}


class AnyPrefixLineItemAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
    search_fields = ("name",)
    display_id_search_fields: ClassVar = {"invoice_id": None}


@pytest.mark.django_db
class TestDisplayIDSearchFields:
    @pytest.fixture
    def invoice(self):
        return Invoice.objects.create(name="Invoice")

    @pytest.fixture
    def product(self):
        return Product.objects.create(name="Product", handle="widget")

    @pytest.fixture
    def line(self, invoice, product):
        line = LineItem.objects.create(name="Line", invoice=invoice)
        line.products.add(product)
        LineItem.objects.create(name="Other line")
        return line

    def search(self, admin_site, term, admin_class=LineItemAdmin, queryset=None):
        """Return (rows, use_distinct)."""
        if queryset is None:
            queryset = LineItem.objects.all()
        model_admin = admin_class(LineItem, admin_site)
        results, use_distinct = model_admin.get_search_results(None, queryset, term)
        return list(results), use_distinct

    @pytest.mark.parametrize("form", ["display_id", "uuid"])
    def test_foreign_key(self, admin_site, line, invoice, form):
        term = invoice.display_id if form == "display_id" else str(invoice.id)
        assert self.search(admin_site, term)[0] == [line]

    def test_many_to_many(self, admin_site, line, product):
        assert self.search(admin_site, product.display_id)[0] == [line]

    def test_distinct_only_for_many_to_many(self, admin_site, line, invoice, product):
        """Like search_fields, a many-to-many path can return a row twice, so
        the admin needs distinct(). An inv_ ID only reaches the foreign key."""
        assert self.search(admin_site, product.display_id)[1] is True
        assert self.search(admin_site, invoice.display_id)[1] is False

    def test_own_identifier_still_matches(self, admin_site, line):
        assert self.search(admin_site, str(line.uid))[0] == [line]

    def test_prefix_must_match_the_model(self, admin_site, line, invoice):
        """invoice_id takes inv_ IDs, and no product has the invoice's UUID."""
        term = encode_display_id("prod", invoice.id)
        assert self.search(admin_site, term)[0] == []

    def test_none_accepts_any_prefix(self, admin_site, line, invoice):
        term = encode_display_id("req", invoice.id)
        assert self.search(admin_site, term, AnyPrefixLineItemAdmin)[0] == [line]

    def test_display_id_type(self, admin_site, line):
        """A DisplayIDType checks its prefix, like a model."""
        own = Reference.encode(line.uid)
        other = encode_display_id("evt", line.uid)
        assert self.search(admin_site, own, TypedLineItemAdmin)[0] == [line]
        assert self.search(admin_site, other, TypedLineItemAdmin)[0] == []

    def test_respects_queryset_scoping(self, admin_site, line, invoice):
        queryset = LineItem.objects.exclude(pk=line.pk)
        assert self.search(admin_site, invoice.display_id, queryset=queryset)[0] == []


class TestParseSearchUUID:
    """The static helper for searching other UUID fields."""

    uid = uuid.uuid4()
    parse = staticmethod(DisplayIDAdminSearchMixin.parse_search_uuid)

    @pytest.mark.parametrize(
        "term",
        [
            encode_display_id("inv", uid),
            str(uid),
            str(uid).upper(),
            f"  {encode_display_id('inv', uid)}\n",
            f"  {uid}\n",
        ],
    )
    def test_parses(self, term):
        assert self.parse(term) == self.uid

    @pytest.mark.parametrize(
        "term",
        [
            "hello world",
            "inv_notvalid",
            "",
            "   ",
            f"inv_ {encode_display_id('inv', uid)}",  # interior whitespace
            uid.hex,  # only the hyphenated form is a UUID
        ],
    )
    def test_returns_none(self, term):
        assert self.parse(term) is None

    def test_model_prefix_must_match(self):
        """With model=, display IDs must use that model's prefix."""
        assert self.parse(encode_display_id("inv", self.uid), model=Invoice) == self.uid
        assert self.parse(encode_display_id("prod", self.uid), model=Invoice) is None
        assert self.parse(str(self.uid), model=Invoice) == self.uid

    def test_display_id_type(self):
        ref = DisplayIDType("ref")
        assert self.parse(ref.encode(self.uid), model=ref) == self.uid
        assert self.parse(encode_display_id("evt", self.uid), model=ref) is None
        assert self.parse(str(self.uid), model=ref) == self.uid

    def test_model_without_prefix_matches_uuids_only(self):
        assert self.parse(encode_display_id("inv", self.uid), model=Order) is None
        assert self.parse(str(self.uid), model=Order) == self.uid

    def test_old_name_warns_and_still_works(self):
        term = encode_display_id("prod", self.uid)
        with pytest.warns(DeprecationWarning, match="parse_search_uuid"):
            assert DisplayIDAdminSearchMixin._parse_identifier(term) == self.uid
        with pytest.warns(DeprecationWarning):
            assert (
                DisplayIDAdminSearchMixin._parse_identifier(term, model=Invoice) is None
            )
