"""Every lookup entry point should accept and reject the same identifiers.

Each ``via_*`` function looks up ``value`` on ``model`` through one entry
point and returns the object, or None for "no match". Configuration errors
(ImproperlyConfigured) are raised, not turned into None. Options use the
mixins' attribute names and are mapped for the other entry points.
"""

import uuid

import pytest
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.views.generic import DetailView
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from django_display_ids import (
    DisplayIDAdminSearchMixin,
    DisplayIDLookupError,
    resolve_object,
    resolve_objects,
)
from django_display_ids.contrib.rest_framework import DisplayIDMixin as DRFMixin
from django_display_ids.contrib.rest_framework import DisplayIDRelatedField
from django_display_ids.encoding import encode_display_id
from django_display_ids.views import DisplayIDMixin

from .models import Invoice, Order, Product, Tag

UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


def _no_match(exc):
    """Lookup errors mean "no match"; configuration errors must surface."""
    if isinstance(exc, ImproperlyConfigured):
        raise exc
    return None


def via_resolver(
    model, value, lookup_strategies=None, display_id_prefix=None, **fields
):
    try:
        return resolve_object(
            model,
            value,
            strategies=lookup_strategies,
            prefix=display_id_prefix,
            **fields,
        )
    except DisplayIDLookupError as e:
        return _no_match(e)


def via_resolve_objects(
    model, value, lookup_strategies=None, display_id_prefix=None, **fields
):
    return resolve_objects(
        model,
        [value],
        strategies=lookup_strategies,
        prefix=display_id_prefix,
        **fields,
    )[value]


def via_get_by_identifier(model, value, lookup_strategies=None, display_id_prefix=None):
    try:
        return model.objects.get_by_identifier(
            value, strategies=lookup_strategies, prefix=display_id_prefix
        )
    except model.DoesNotExist:
        return None


def via_filter_by_identifier(
    model, value, lookup_strategies=None, display_id_prefix=None
):
    return model.objects.filter_by_identifier(
        value, strategies=lookup_strategies, prefix=display_id_prefix
    ).first()


def via_resolve_uuid(model, value, lookup_strategies=None, display_id_prefix=None):
    try:
        uid = model.objects.resolve_uuid(
            value, strategies=lookup_strategies, prefix=display_id_prefix
        )
    except model.DoesNotExist:
        return None
    uuid_field = getattr(model, "uuid_field", None) or "id"
    return model.objects.filter(**{uuid_field: uid}).first()


def via_get_by_identifiers(
    model, value, lookup_strategies=None, display_id_prefix=None
):
    return model.objects.get_by_identifiers(
        [value], strategies=lookup_strategies, prefix=display_id_prefix
    ).first()


def via_admin(model, value, **options):
    # search_fields never match the test values, so admin can only find rows
    # through the display ID / UUID / slug search
    admin_class = type(
        "Admin",
        (DisplayIDAdminSearchMixin, admin.ModelAdmin),
        {"search_fields": ("name",), **options},
    )
    qs, _ = admin_class(model, admin.site).get_search_results(
        None, model.objects.all(), value
    )
    return qs.first()


def via_django_view(model, value, **options):
    view_class = type(
        "View",
        (DisplayIDMixin, DetailView),
        {"model": model, "lookup_url_kwarg": "id", **options},
    )
    view = view_class()
    view.kwargs = {"id": value}
    try:
        return view.get_object()
    except Http404:
        return None


def via_drf_view(model, value, **options):
    view_class = type(
        "View",
        (DRFMixin, APIView),
        {
            "lookup_url_kwarg": "id",
            "get_queryset": lambda _self: model.objects.all(),
            **options,
        },
    )
    view = view_class()
    view.kwargs = {"id": value}
    view.request = None
    try:
        return view.get_object()
    except Http404:
        return None


def via_related_field(model, value, **options):
    field = DisplayIDRelatedField(queryset=model.objects.all(), **options)
    try:
        return field.to_internal_value(value)
    except ValidationError:
        return None


def via_related_field_many(model, value, **options):
    field = DisplayIDRelatedField(queryset=model.objects.all(), many=True, **options)
    try:
        [obj] = field.to_internal_value([value])
    except ValidationError:
        return None
    return obj


ENTRY_POINTS = [
    via_resolver,
    via_resolve_objects,
    via_get_by_identifier,
    via_filter_by_identifier,
    via_resolve_uuid,
    via_get_by_identifiers,
    via_admin,
    via_django_view,
    via_drf_view,
    via_related_field,
    via_related_field_many,
]

# Entry points that take every lookup attribute, not just strategies/prefix
WITH_FIELD_OPTIONS = [
    via_resolver,
    via_resolve_objects,
    via_admin,
    via_django_view,
    via_drf_view,
    via_related_field,
    via_related_field_many,
]

UUID_FORMS = {
    "lowercase": str(UUID),
    "uppercase": str(UUID).upper(),
    "mixed case": str(UUID)[:18].upper() + str(UUID)[18:],
    "padded": f"  {UUID}\n",
}

# Only the hyphenated form counts as a UUID. These are ordinary strings, so
# they can only match as slugs.
NOT_UUID_FORMS = {
    "no hyphens": UUID.hex,
    "no hyphens uppercase": UUID.hex.upper(),
    "some hyphens missing": UUID.hex[:8] + "-" + UUID.hex[8:],
    "braces": f"{{{UUID}}}",
    "urn": UUID.urn,
}


@pytest.fixture
def invoice(db):
    return Invoice.objects.create(id=UUID, name="invoice", slug="march-invoice")


@pytest.fixture
def order(db):
    return Order.objects.create(id=UUID, name="order")


@pytest.fixture
def tag(db):
    return Tag.objects.create(id=UUID, name="tag")


@pytest.fixture
def product(db):
    return Product.objects.create(uid=UUID, name="product", handle="widget")


@pytest.mark.parametrize("lookup", ENTRY_POINTS)
class TestConsistency:
    @pytest.mark.parametrize("value", UUID_FORMS.values(), ids=UUID_FORMS.keys())
    def test_uuid_forms_match(self, lookup, invoice, value):
        assert lookup(Invoice, value) == invoice

    @pytest.mark.parametrize(
        "value", NOT_UUID_FORMS.values(), ids=NOT_UUID_FORMS.keys()
    )
    def test_other_uuid_forms_do_not_match(self, lookup, invoice, value):
        assert lookup(Invoice, value) is None

    def test_hex_slug_matches_as_slug(self, lookup, invoice):
        """A slug that looks like an unhyphenated UUID (here an MD5 hash) is
        still a slug, not a UUID."""
        md5 = Invoice.objects.create(
            name="md5", slug="d41d8cd98f00b204e9800998ecf8427e"
        )
        assert lookup(Invoice, "d41d8cd98f00b204e9800998ecf8427e") == md5

    def test_display_id_matches(self, lookup, invoice):
        assert lookup(Invoice, invoice.display_id) == invoice

    def test_padded_display_id_matches(self, lookup, invoice):
        assert lookup(Invoice, f" {invoice.display_id} ") == invoice

    def test_wrong_prefix_does_not_match(self, lookup, invoice):
        assert lookup(Invoice, encode_display_id("cust", UUID)) is None

    def test_missing_row_does_not_match(self, lookup, invoice):
        assert lookup(Invoice, str(uuid.uuid4())) is None

    def test_slug_matches(self, lookup, invoice):
        assert lookup(Invoice, "march-invoice") == invoice

    def test_partial_slug_does_not_match(self, lookup, invoice):
        assert lookup(Invoice, "march") is None

    def test_strategies_setting_is_honored(self, lookup, invoice, settings):
        settings.DISPLAY_IDS = {"STRATEGIES": ("display_id",)}
        assert lookup(Invoice, invoice.display_id) == invoice
        assert lookup(Invoice, str(UUID)) is None
        assert lookup(Invoice, "march-invoice") is None

    def test_custom_uuid_and_slug_fields(self, lookup, product):
        """Product keeps its UUID in uid and its slug in handle."""
        assert lookup(Product, product.display_id) == product
        assert lookup(Product, str(UUID)) == product
        assert lookup(Product, "widget") == product

    def test_model_without_slug_field(self, lookup, tag):
        """Slugs are skipped, but UUIDs and display IDs still work."""
        assert lookup(Tag, tag.display_id) == tag
        assert lookup(Tag, str(UUID)) == tag
        assert lookup(Tag, "some-slug") is None

    def test_slug_only_without_slug_field_raises(self, lookup, tag):
        """A lookup that can never match is a configuration error."""
        with pytest.raises(ImproperlyConfigured, match="no 'slug' field"):
            lookup(Tag, "some-slug", lookup_strategies=("slug",))


@pytest.mark.parametrize(
    "lookup",
    [e for e in ENTRY_POINTS if e not in (via_related_field, via_related_field_many)],
)
class TestModelWithoutPrefix:
    """DisplayIDRelatedField refuses models without a prefix by design."""

    def test_display_id_does_not_match(self, lookup, invoice, order):
        """Order shares Invoice's UUID but has no prefix, so inv_ must not match."""
        assert lookup(Order, invoice.display_id) is None

    def test_uuid_matches(self, lookup, order):
        assert lookup(Order, str(UUID)) == order

    def test_display_id_only_raises(self, lookup, order):
        with pytest.raises(ImproperlyConfigured):
            lookup(Order, str(UUID), lookup_strategies=("display_id",))


@pytest.mark.parametrize("lookup", WITH_FIELD_OPTIONS)
class TestOptions:
    """Each option wins over the model's own setting."""

    def test_display_id_prefix(self, lookup, invoice):
        assert lookup(
            Invoice, encode_display_id("bill", UUID), display_id_prefix="bill"
        )
        assert lookup(Invoice, invoice.display_id, display_id_prefix="bill") is None

    def test_uuid_field(self, lookup, invoice):
        """Pointing uuid_field at the slug column makes UUID lookups miss."""
        options = {"uuid_field": "slug", "lookup_strategies": ("uuid",)}
        assert lookup(Invoice, str(UUID), **options) is None

    def test_slug_field(self, lookup, product):
        """Product's own slug_field is "handle"; the option uses "name"."""
        assert lookup(Product, "product", slug_field="name") == product

    def test_lookup_strategies(self, lookup, invoice):
        options = {"lookup_strategies": ("uuid",)}
        assert lookup(Invoice, str(UUID), **options) == invoice
        assert lookup(Invoice, invoice.display_id, **options) is None
        assert lookup(Invoice, "march-invoice", **options) is None

    @pytest.mark.parametrize("prefix", ["", "Invalid123", "waytoolongprefix123"])
    def test_invalid_prefix(self, lookup, invoice, prefix):
        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            lookup(Invoice, invoice.display_id, display_id_prefix=prefix)
