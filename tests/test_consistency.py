"""Every lookup entry point should accept and reject the same identifiers."""

import uuid

import pytest
from django.contrib import admin
from django.http import Http404
from django.views.generic import DetailView
from rest_framework.views import APIView

from django_display_ids import (
    DisplayIDAdminSearchMixin,
    DisplayIDLookupError,
    resolve_object,
)
from django_display_ids.contrib.rest_framework import DisplayIDMixin as DRFMixin
from django_display_ids.encoding import encode_display_id
from django_display_ids.views import DisplayIDMixin

from .models import Invoice, Order

UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


def via_resolver(model, value):
    try:
        return resolve_object(model, value)
    except DisplayIDLookupError:
        return None


def via_get_by_identifier(model, value):
    try:
        return model.objects.get_by_identifier(value)
    except model.DoesNotExist:
        return None


def via_resolve_identifier(model, value):
    try:
        uid = model.objects.resolve_identifier(value)
    except model.DoesNotExist:
        return None
    return model.objects.filter(pk=uid).first()


def via_get_by_identifiers(model, value):
    try:
        return model.objects.get_by_identifiers([value]).first()
    except DisplayIDLookupError:
        return None


def via_admin(model, value):
    class Admin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
        search_fields = ("name",)

    qs, _ = Admin(model, admin.site).get_search_results(
        None, model.objects.all(), value
    )
    return qs.first()


def via_django_view(model, value):
    class View(DisplayIDMixin, DetailView):
        lookup_url_kwarg = "id"

    View.model = model
    view = View()
    view.kwargs = {"id": value}
    try:
        return view.get_object()
    except Http404:
        return None


def via_drf_view(model, value):
    class View(DRFMixin, APIView):
        lookup_url_kwarg = "id"

        def get_queryset(self):
            return model.objects.all()

    view = View()
    view.kwargs = {"id": value}
    view.request = None
    try:
        return view.get_object()
    except Http404:
        return None


ENTRY_POINTS = [
    via_resolver,
    via_get_by_identifier,
    via_resolve_identifier,
    via_get_by_identifiers,
    via_admin,
    via_django_view,
    via_drf_view,
]

UUID_FORMS = {
    "lowercase": str(UUID),
    "uppercase": str(UUID).upper(),
    "no hyphens": UUID.hex,
    "no hyphens uppercase": UUID.hex.upper(),
    "braces": f"{{{UUID}}}",
    "urn": UUID.urn,
    "padded": f"  {UUID}\n",
}


@pytest.fixture
def invoice(db):
    # The name never matches the search terms, so admin can only
    # find this row through the display ID / UUID / slug search.
    return Invoice.objects.create(id=UUID, name="invoice", slug="march-invoice")


@pytest.fixture
def order(db):
    return Order.objects.create(id=UUID, name="order")


@pytest.mark.parametrize("lookup", ENTRY_POINTS)
class TestConsistency:
    @pytest.mark.parametrize("value", UUID_FORMS.values(), ids=UUID_FORMS.keys())
    def test_uuid_forms_match(self, lookup, invoice, value):
        assert lookup(Invoice, value) == invoice

    def test_display_id_matches(self, lookup, invoice):
        assert lookup(Invoice, invoice.display_id) == invoice

    def test_padded_display_id_matches(self, lookup, invoice):
        assert lookup(Invoice, f" {invoice.display_id} ") == invoice

    def test_wrong_prefix_does_not_match(self, lookup, invoice):
        assert lookup(Invoice, encode_display_id("cust", UUID)) is None

    def test_display_id_does_not_match_model_without_prefix(
        self, lookup, invoice, order
    ):
        """Order shares Invoice's UUID but has no prefix, so inv_ must not match."""
        assert lookup(Order, invoice.display_id) is None

    def test_uuid_matches_model_without_prefix(self, lookup, order):
        assert lookup(Order, str(UUID)) == order

    def test_slug_matches(self, lookup, invoice):
        assert lookup(Invoice, "march-invoice") == invoice

    def test_partial_slug_does_not_match(self, lookup, invoice):
        assert lookup(Invoice, "march") is None

    def test_strategies_setting_is_honored(self, lookup, invoice, settings):
        settings.DISPLAY_IDS = {"STRATEGIES": ("display_id",)}
        assert lookup(Invoice, invoice.display_id) == invoice
        assert lookup(Invoice, str(UUID)) is None
        assert lookup(Invoice, "march-invoice") is None
