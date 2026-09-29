"""Tests for the admin search mixin.

Which identifier forms are accepted or rejected, and how each option (prefix,
strategies, fields) overrides the model, is covered for every entry
point in test_consistency.py. These tests cover admin-specific behavior.
"""

import uuid

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite

from django_display_ids import DisplayIDAdminSearchMixin, encode_display_id

from .models import Invoice, Order


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
