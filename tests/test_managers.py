"""Tests for the manager and queryset methods.

Which identifier forms are accepted or rejected is covered for every entry
point in test_consistency.py. These tests cover manager-specific behavior:
UUID objects, explicit arguments, filtered querysets, batch lookups and
query counts.
"""

import uuid

import pytest
from django.core.exceptions import ObjectDoesNotExist

from django_display_ids.encoding import encode_display_id
from django_display_ids.exceptions import MissingPrefixError
from django_display_ids.managers import DisplayIDQuerySet

from .models import Invoice, Order, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def other(db):
    """A second invoice, for checks that the right one is picked."""
    return Invoice.objects.create(name="Other Invoice", slug="other-invoice")


class TestGetByDisplayId:
    def test_found(self, invoice, product):
        assert Invoice.objects.get_by_display_id(invoice.display_id) == invoice
        # Product keeps its UUID in uid
        assert Product.objects.get_by_display_id(product.display_id) == product

    @pytest.mark.parametrize(
        "value",
        [
            encode_display_id("inv", uuid.uuid4()),  # no such row
            "invalid-format",
            encode_display_id("prod", uuid.uuid4()),  # wrong prefix
        ],
    )
    def test_not_found(self, invoice, value):
        with pytest.raises(Invoice.DoesNotExist):
            Invoice.objects.get_by_display_id(value)

    def test_explicit_prefix(self, invoice):
        custom = encode_display_id("custom", invoice.id)
        assert Invoice.objects.get_by_display_id(custom, prefix="custom") == invoice

    def test_model_without_prefix_raises(self, order):
        with pytest.raises(MissingPrefixError) as exc_info:
            Order.objects.get_by_display_id(encode_display_id("ord", order.id))
        assert exc_info.value.model_name == "Order"


class TestGetByIdentifier:
    def test_explicit_strategies(self, invoice):
        slug_only = {"strategies": ("slug",)}
        assert Invoice.objects.get_by_identifier("test-invoice", **slug_only) == invoice
        with pytest.raises(Invoice.DoesNotExist):
            Invoice.objects.get_by_identifier(invoice.display_id, **slug_only)

    def test_explicit_prefix(self, invoice):
        custom = encode_display_id("custom", invoice.id)
        assert Invoice.objects.get_by_identifier(custom, prefix="custom") == invoice

    def test_does_not_exist_is_an_object_does_not_exist(self, invoice):
        """Like QuerySet.get(), misses raise Model.DoesNotExist."""
        with pytest.raises(ObjectDoesNotExist):
            Invoice.objects.get_by_identifier(str(uuid.uuid4()))


class TestFilterByIdentifier:
    def test_returns_display_id_queryset(self, invoice):
        """So get_by_identifier() and friends can be chained after it."""
        result = Invoice.objects.filter_by_identifier(invoice.display_id)
        assert isinstance(result, DisplayIDQuerySet)

    def test_uuid_object(self, invoice, other):
        assert list(Invoice.objects.filter_by_identifier(invoice.id)) == [invoice]

    def test_explicit_strategies(self, invoice):
        slug_only = {"strategies": ("slug",)}
        assert list(Invoice.objects.filter_by_identifier("test-invoice", **slug_only))
        assert not Invoice.objects.filter_by_identifier(invoice.display_id, **slug_only)

    def test_explicit_prefix(self, invoice):
        custom = encode_display_id("custom", invoice.id)
        result = Invoice.objects.filter_by_identifier(custom, prefix="custom")
        assert list(result) == [invoice]

    @pytest.mark.parametrize(
        "bad", ["not a valid identifier!", encode_display_id("prod", uuid.uuid4())]
    )
    def test_rejected_identifier_runs_no_query(
        self, invoice, bad, django_assert_num_queries
    ):
        """Rejected input is known not to match, so there is nothing to query."""
        result = Invoice.objects.filter_by_identifier(
            bad, strategies=("display_id", "uuid")
        )
        with django_assert_num_queries(0):
            assert list(result) == []


@pytest.mark.parametrize("method", ["get_by_display_id", "get_by_identifier"])
class TestUUIDObjects:
    def test_found(self, invoice, method):
        assert getattr(Invoice.objects, method)(invoice.id) == invoice

    def test_not_found(self, invoice, method):
        with pytest.raises(Invoice.DoesNotExist):
            getattr(Invoice.objects, method)(uuid.uuid4())


def test_uuid_object_on_model_without_prefix(order):
    """UUID objects skip strategies, so display_id being unusable doesn't matter."""
    assert Order.objects.get_by_identifier(order.id) == order


def test_filtered_queryset(invoice, other):
    """Each method only searches the queryset it's called on."""
    queryset = Invoice.objects.filter(slug="test-invoice")

    assert queryset.get_by_display_id(invoice.display_id) == invoice
    assert queryset.get_by_identifier(invoice.display_id) == invoice
    assert queryset.resolve_uuid("test-invoice") == invoice.id
    assert list(queryset.filter_by_identifier(invoice.display_id)) == [invoice]
    assert not queryset.filter_by_identifier(other.display_id)

    with pytest.raises(Invoice.DoesNotExist):
        queryset.get_by_display_id(other.display_id)
    with pytest.raises(Invoice.DoesNotExist):
        queryset.get_by_identifier(other.display_id)
    with pytest.raises(Invoice.DoesNotExist):
        queryset.resolve_uuid("other-invoice")  # slugs need a query


class TestGetByIdentifiers:
    def test_empty_list(self, invoice):
        assert list(Invoice.objects.get_by_identifiers([])) == []

    @pytest.mark.parametrize(
        "form",
        [lambda i: i.display_id, lambda i: str(i.id), lambda i: i.id, lambda i: i.slug],
        ids=["display_id", "uuid_string", "uuid_object", "slug"],
    )
    def test_each_form(self, invoice, other, form):
        Invoice.objects.create(name="Not requested", slug="not-requested")
        result = Invoice.objects.get_by_identifiers([form(invoice), form(other)])
        assert set(result) == {invoice, other}

    def test_mixed_forms_in_one_query(self, invoice, other, django_assert_num_queries):
        third = Invoice.objects.create(name="Third", slug="third")
        with django_assert_num_queries(1):
            result = set(
                Invoice.objects.get_by_identifiers(
                    [invoice.id, other.display_id, "third"]
                )
            )
        assert result == {invoice, other, third}

    @pytest.mark.parametrize(
        "bad",
        [
            str(uuid.uuid4()),  # no such row
            "not a valid identifier!",
            encode_display_id("prod", uuid.uuid4()),  # wrong prefix
        ],
    )
    def test_bad_identifiers_are_left_out(self, invoice, bad):
        """Left out like missing rows, not raised; see get_by_identifier."""
        result = Invoice.objects.get_by_identifiers(
            [bad, invoice.display_id], strategies=("display_id", "uuid")
        )
        assert list(result) == [invoice]

    def test_all_invalid_returns_empty(self, invoice):
        """An empty filter would match every row, so this must return none."""
        result = Invoice.objects.get_by_identifiers(
            ["nope", encode_display_id("prod", uuid.uuid4())],
            strategies=("display_id", "uuid"),
        )
        assert list(result) == []

    def test_filtered_queryset(self, invoice, other):
        queryset = Invoice.objects.filter(slug="test-invoice")
        result = queryset.get_by_identifiers([invoice.display_id, other.display_id])
        assert list(result) == [invoice]

    def test_explicit_prefix(self, invoice):
        custom = encode_display_id("custom", invoice.id)
        result = Invoice.objects.get_by_identifiers([custom], prefix="custom")
        assert list(result) == [invoice]


class TestResolveUUID:
    @pytest.mark.parametrize(
        "source", [lambda: Invoice.objects, lambda: Invoice.objects.all()]
    )
    def test_old_name_warns_and_still_works(self, invoice, source):
        with pytest.warns(DeprecationWarning, match="resolve_uuid") as record:
            assert source().resolve_identifier(invoice.display_id) == invoice.id
        # Points at the caller, not at the library
        assert record[0].filename == __file__

    def test_returns_uuid(self, invoice):
        result = Invoice.objects.resolve_uuid(str(invoice.id))
        assert isinstance(result, uuid.UUID)
        assert result == invoice.id
        assert Invoice.objects.resolve_uuid(invoice.id) is invoice.id

    def test_uuid_existence_not_checked(self, invoice):
        """A UUID or display ID is returned without checking the row exists."""
        fake = uuid.uuid4()
        assert Invoice.objects.resolve_uuid(str(fake)) == fake

    def test_slug(self, invoice):
        assert Invoice.objects.resolve_uuid("test-invoice") == invoice.id
        with pytest.raises(Invoice.DoesNotExist):
            Invoice.objects.resolve_uuid("nonexistent-slug")

    def test_explicit_prefix(self, invoice):
        custom = encode_display_id("custom", invoice.id)
        assert Invoice.objects.resolve_uuid(custom, prefix="custom") == invoice.id

    @pytest.mark.parametrize(
        ("form", "queries"),
        [
            (lambda i: i.display_id, 0),
            (lambda i: str(i.id), 0),
            (lambda i: i.id, 0),
            (lambda i: i.slug, 1),
        ],
        ids=["display_id", "uuid_string", "uuid_object", "slug"],
    )
    def test_query_count(self, invoice, django_assert_num_queries, form, queries):
        """Only slugs need the database."""
        with django_assert_num_queries(queries):
            Invoice.objects.resolve_uuid(form(invoice))
