"""Tests for the Django view mixin.

Which identifier forms are accepted or rejected, and how each option (prefix,
strategies, fields) overrides the model, is covered for every entry
point in test_consistency.py. These tests cover view-specific behavior.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured, MultipleObjectsReturned
from django.http import Http404
from django.views.generic import DetailView, View

from django_display_ids.views import DisplayIDMixin

from .models import Invoice, Order


def get_object(view_class, value, rf, kwarg="id"):
    view = view_class()
    view.kwargs = {kwarg: value}
    view.request = rf.get("/")
    return view.get_object()


class InvoiceDetailView(DisplayIDMixin, DetailView):
    model = Invoice
    lookup_url_kwarg = "id"


@pytest.mark.django_db
class TestGetObject:
    def test_missing_url_kwarg(self, rf, invoice):
        """A missing URL parameter is a URLconf bug, not a 404."""
        with pytest.raises(AttributeError, match="'id' URL parameter"):
            get_object(InvoiceDetailView, invoice.display_id, rf, kwarg="pk")

    def test_custom_url_kwarg(self, rf, invoice):
        class View(InvoiceDetailView):
            lookup_url_kwarg = "invoice_id"

        assert get_object(View, invoice.display_id, rf, kwarg="invoice_id") == invoice

    def test_ambiguous_slug_raises(self, rf):
        """Duplicate slugs raise like Django's get_object() instead of 404ing."""
        # name isn't unique, so use it as the slug field to get duplicates
        Order.objects.create(name="dup")
        Order.objects.create(name="dup")

        class View(DisplayIDMixin, DetailView):
            model = Order
            lookup_url_kwarg = "id"
            slug_field = "name"

        with pytest.raises(MultipleObjectsReturned):
            get_object(View, "dup", rf)


@pytest.mark.django_db
class TestQueryset:
    def test_get_queryset_is_respected(self, rf):
        visible = Invoice.objects.create(name="Visible", slug="visible")
        hidden = Invoice.objects.create(name="Hidden", slug="hidden")

        class View(InvoiceDetailView):
            def get_queryset(self):
                return Invoice.objects.filter(slug="visible")

        assert get_object(View, visible.display_id, rf) == visible
        with pytest.raises(Http404):
            get_object(View, hidden.display_id, rf)

    def test_queryset_without_model(self, rf, invoice):
        """The model is taken from the queryset when not set on the view."""

        class View(DisplayIDMixin, DetailView):
            queryset = Invoice.objects.all()
            lookup_url_kwarg = "id"

        assert get_object(View, invoice.display_id, rf) == invoice

    def test_neither_model_nor_queryset(self, rf):
        """Django's own ImproperlyConfigured is raised with neither set."""

        class View(DisplayIDMixin, DetailView):
            lookup_url_kwarg = "id"

        with pytest.raises(ImproperlyConfigured):
            get_object(View, "test", rf)

    def test_without_single_object_mixin(self, rf, invoice):
        """On a plain View, the mixin falls back to model._default_manager."""

        class PlainView(DisplayIDMixin, View):
            model = Invoice
            lookup_url_kwarg = "id"

        assert get_object(PlainView, invoice.display_id, rf) == invoice

    def test_without_single_object_mixin_or_model(self, rf):
        class PlainView(DisplayIDMixin, View):
            lookup_url_kwarg = "id"

        with pytest.raises(AttributeError, match="must define 'model'"):
            get_object(PlainView, "test", rf)


def test_old_lookup_param_name_fails_at_class_definition():
    """lookup_param was renamed to lookup_url_kwarg in 0.8."""
    with pytest.raises(TypeError, match="renamed to lookup_url_kwarg"):

        class OldStyleView(DisplayIDMixin, DetailView):
            model = Invoice
            lookup_param = "id"
