"""Tests for DisplayIDRelatedField."""

import uuid

import pytest
from rest_framework import serializers

from django_display_ids.contrib.rest_framework import DisplayIDRelatedField
from django_display_ids.encoding import encode_display_id
from django_display_ids.exceptions import MissingPrefixError

from .models import Invoice, LineItem, Order, Product


class LineItemSerializer(serializers.ModelSerializer):
    invoice = DisplayIDRelatedField(
        queryset=Invoice.objects.all(), allow_null=True, required=False
    )
    products = DisplayIDRelatedField(
        queryset=Product.objects.all(), many=True, required=False
    )

    class Meta:
        model = LineItem
        fields = ("name", "invoice", "products")


class ReadOnlyLineItemSerializer(serializers.ModelSerializer):
    """No querysets, so the fields have to find their model from the serializer."""

    invoice = DisplayIDRelatedField(read_only=True)
    products = DisplayIDRelatedField(read_only=True, many=True)

    class Meta:
        model = LineItem
        fields = ("invoice", "products")


@pytest.mark.django_db
class TestOutput:
    def test_foreign_key_is_display_id(self, invoice):
        item = LineItem.objects.create(name="x", invoice=invoice)
        assert LineItemSerializer(item).data["invoice"] == invoice.display_id

    def test_null_foreign_key_is_none(self):
        item = LineItem.objects.create(name="x")
        assert LineItemSerializer(item).data["invoice"] is None

    def test_many_uses_custom_uuid_field(self, product):
        """Product keeps its UUID in uid, not the primary key."""
        item = LineItem.objects.create(name="x")
        item.products.add(product)
        assert LineItemSerializer(item).data["products"] == [product.display_id]

    def test_no_query_per_foreign_key(self, invoice, django_assert_num_queries):
        """When the UUID is the primary key, the FK column is enough."""
        for i in range(3):
            LineItem.objects.create(name=str(i), invoice=invoice)

        class InvoiceOnly(serializers.ModelSerializer):
            invoice = DisplayIDRelatedField(queryset=Invoice.objects.all())

            class Meta:
                model = LineItem
                fields = ("invoice",)

        items = list(LineItem.objects.all())
        with django_assert_num_queries(0):
            data = InvoiceOnly(items, many=True).data
        assert [row["invoice"] for row in data] == [invoice.display_id] * 3

    def test_read_only_without_queryset(self, invoice, product):
        item = LineItem.objects.create(name="x", invoice=invoice)
        item.products.add(product)
        data = ReadOnlyLineItemSerializer(item).data
        assert data["invoice"] == invoice.display_id
        assert data["products"] == [product.display_id]


@pytest.mark.django_db
class TestInput:
    @pytest.mark.parametrize(
        "value",
        [
            "not-a-real-slug",  # parses as a slug, no row
            encode_display_id("prod", uuid.uuid4()),  # wrong prefix, fails parsing
            encode_display_id("inv", uuid.uuid4()),  # valid display ID, no row
            str(uuid.uuid4()),  # valid UUID, no row
        ],
        ids=["unknown_slug", "wrong_prefix", "unknown_display_id", "unknown_uuid"],
    )
    def test_no_match_is_does_not_exist(self, invoice, value):
        """Every kind of no-match uses DRF's does_not_exist error code, whether
        it fails while parsing or at the database query."""
        s = LineItemSerializer(data={"name": "x", "invoice": value})
        assert not s.is_valid()
        assert s.errors["invoice"][0].code == "does_not_exist"

    @pytest.mark.parametrize("value", [123, True, ["inv_x"]])
    def test_rejects_wrong_type(self, invoice, value):
        s = LineItemSerializer(data={"name": "x", "invoice": value})
        assert not s.is_valid()
        assert s.errors["invoice"][0].code == "incorrect_type"

    def test_duplicate_slug_raises(self):
        """Like DRF's SlugRelatedField: duplicate slugs are a data problem, so
        they raise instead of becoming a validation error blaming the client."""
        from django.core.exceptions import MultipleObjectsReturned

        # name isn't unique, so use it as the slug field to get duplicates
        Order.objects.create(name="dup")
        Order.objects.create(name="dup")
        field = DisplayIDRelatedField(
            queryset=Order.objects.all(), display_id_prefix="ord", slug_field="name"
        )
        with pytest.raises(MultipleObjectsReturned):
            field.to_internal_value("dup")

    def test_many(self, product):
        other = Product.objects.create(name="Other", handle="gadget")
        s = LineItemSerializer(
            data={"name": "x", "products": [product.display_id, "gadget"]}
        )
        assert s.is_valid(), s.errors
        item = s.save()
        assert set(item.products.all()) == {product, other}

    def test_round_trip(self, invoice, product):
        """A client can send back exactly what it read."""
        item = LineItem.objects.create(name="x", invoice=invoice)
        item.products.add(product)
        data = dict(LineItemSerializer(item).data)

        s = LineItemSerializer(item, data=data)
        assert s.is_valid(), s.errors
        s.save()
        assert s.data == data


@pytest.mark.django_db
class TestOptions:
    @pytest.mark.parametrize(
        ("model", "prefix"),
        [(Invoice, "bill"), (Order, "ord")],  # Order has no prefix of its own
    )
    def test_display_id_prefix(self, model, prefix):
        obj = model.objects.create(name="x")
        field = DisplayIDRelatedField(
            queryset=model.objects.all(), display_id_prefix=prefix
        )
        display_id = encode_display_id(prefix, obj.id)
        assert field.to_representation(obj) == display_id
        assert field.to_internal_value(display_id) == obj

    def test_model_without_prefix_fails_at_definition(self):
        with pytest.raises(MissingPrefixError):
            DisplayIDRelatedField(queryset=Order.objects.all())


@pytest.mark.django_db
class TestOpenApiSchema:
    @pytest.fixture(autouse=True)
    def _spectacular(self):
        pytest.importorskip("drf_spectacular")

    def _schema(self, field, direction):
        from django_display_ids.contrib.drf_spectacular import (
            DisplayIDRelatedFieldExtension,
        )

        return DisplayIDRelatedFieldExtension(target=field).map_serializer_field(
            None, direction
        )

    def test_response_is_display_id(self):
        field = DisplayIDRelatedField(queryset=Invoice.objects.all())
        schema = self._schema(field, "response")
        assert schema["example"].startswith("inv_")
        assert schema["pattern"] == r"^inv_[0-9A-Za-z]{22}$"

    def test_request_lists_accepted_formats(self):
        field = DisplayIDRelatedField(queryset=Invoice.objects.all())
        schema = self._schema(field, "request")
        assert schema["description"] == (
            "Identifier: display_id (inv_xxx), UUID, or slug"
        )
        assert "pattern" not in schema  # UUIDs and slugs are accepted too

    def test_request_follows_lookup_strategies(self):
        field = DisplayIDRelatedField(
            queryset=Invoice.objects.all(), lookup_strategies=("display_id",)
        )
        schema = self._schema(field, "request")
        assert schema["description"] == "Identifier: display_id (inv_xxx)"
        # Only display IDs are accepted, so the schema can check the format,
        # including the prefix
        assert schema["pattern"] == r"^inv_[0-9A-Za-z]{22}$"

    def test_read_only_field_uses_serializer_model(self):
        fields = ReadOnlyLineItemSerializer().fields
        invoice = self._schema(fields["invoice"], "response")
        assert invoice["example"].startswith("inv_")
        # many=True: the child's parent is a ManyRelatedField, not the serializer
        products = self._schema(fields["products"].child_relation, "response")
        assert products["example"].startswith("prod_")

    def test_many_becomes_array_in_full_schema(self, settings):
        from drf_spectacular.generators import SchemaGenerator
        from rest_framework import viewsets
        from rest_framework.routers import SimpleRouter

        class LineItemViewSet(viewsets.ModelViewSet):
            queryset = LineItem.objects.all()
            serializer_class = LineItemSerializer

        settings.REST_FRAMEWORK = {
            "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"
        }
        router = SimpleRouter()
        router.register("items", LineItemViewSet)
        schema = SchemaGenerator(patterns=router.urls).get_schema(public=True)

        props = schema["components"]["schemas"]["LineItem"]["properties"]
        assert props["invoice"]["nullable"] is True
        assert props["products"]["type"] == "array"
        assert props["products"]["items"]["example"].startswith("prod_")
