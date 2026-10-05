"""Tests for the DRF view mixin and DisplayIDField.

Which identifier forms are accepted or rejected, and how each option (prefix,
strategies, fields) overrides the model, is covered for every entry
point in test_consistency.py. These tests cover DRF-specific behavior.
"""

import os
import subprocess
import sys
import uuid

import pytest
from django.core.exceptions import MultipleObjectsReturned
from django.http import Http404
from rest_framework import permissions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from django_display_ids.contrib.rest_framework import (
    DisplayIDField,
    DisplayIDMixin,
)
from django_display_ids.encoding import encode_display_id
from django_display_ids.examples import example_display_id

from .models import Invoice, Order, Product, Tag

UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


class InvoiceAPIView(DisplayIDMixin, APIView):
    lookup_url_kwarg = "id"

    def get_queryset(self):
        return Invoice.objects.all()

    def get(self, request, *args, **kwargs):
        return Response({"name": self.get_object().name})


@pytest.fixture
def rf():
    return APIRequestFactory()


def get_object(view_class, value, rf, kwarg="id"):
    view = view_class()
    view.kwargs = {kwarg: value}
    view.request = rf.get("/")
    view.format_kwarg = None
    return view.get_object()


@pytest.mark.django_db
class TestGetObject:
    def test_missing_url_kwarg(self, rf, invoice):
        """A missing URL kwarg fails an assertion, like DRF's get_object()."""
        with pytest.raises(AssertionError, match="URL keyword argument named 'id'"):
            get_object(InvoiceAPIView, invoice.display_id, rf, kwarg="pk")

    def test_ambiguous_slug_raises(self, rf):
        """Duplicate slugs raise MultipleObjectsReturned, like DRF."""
        # name isn't unique, so use it as the slug field to get duplicates
        Order.objects.create(name="dup")
        Order.objects.create(name="dup")

        class View(DisplayIDMixin, APIView):
            lookup_url_kwarg = "id"
            slug_field = "name"

            def get_queryset(self):
                return Order.objects.all()

        with pytest.raises(MultipleObjectsReturned):
            get_object(View, "dup", rf)

    def test_filter_backends_applied(self, rf, invoice):
        """filter_queryset() runs before the lookup, like DRF's get_object()."""
        other = Invoice.objects.create(name="Other")

        class OnlyFirstBackend:
            def filter_queryset(self, request, queryset, view):
                return queryset.filter(pk=invoice.pk)

        class View(DisplayIDMixin, GenericAPIView):
            lookup_url_kwarg = "id"
            queryset = Invoice.objects.all()
            filter_backends = (OnlyFirstBackend,)

        with pytest.raises(Http404):
            get_object(View, other.display_id, rf)
        assert get_object(View, invoice.display_id, rf) == invoice

    def test_get_queryset_is_respected(self, rf):
        visible = Invoice.objects.create(name="Visible", slug="visible")
        hidden = Invoice.objects.create(name="Hidden", slug="hidden")

        class View(InvoiceAPIView):
            def get_queryset(self):
                return Invoice.objects.filter(slug="visible")

        assert get_object(View, visible.display_id, rf) == visible
        with pytest.raises(Http404):
            get_object(View, hidden.display_id, rf)

    def test_without_get_queryset(self, rf):
        class View(DisplayIDMixin):
            lookup_url_kwarg = "id"
            request = None

        with pytest.raises(NotImplementedError, match="must override 'get_queryset"):
            get_object(View, "x", rf)


@pytest.mark.django_db
class TestResponses:
    """Through DRF's request handling."""

    @pytest.mark.parametrize(
        "value",
        [
            "not-an-id",
            encode_display_id("prod", uuid.uuid4()),
            str(uuid.uuid4()),
        ],
    )
    def test_404_response(self, rf, value):
        response = InvoiceAPIView.as_view()(rf.get("/"), id=value)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("ours", "drf"),
        [
            # A value DRF can't use as the lookup field: "Not found."
            (encode_display_id("prod", uuid.uuid4()), "not-a-uuid"),
            # A row that doesn't exist: "No Invoice matches the given query."
            (str(UUID), str(UUID)),
        ],
        ids=["unusable", "missing"],
    )
    def test_404_body_matches_drf(self, rf, ours, drf):
        """The 404 body is the one DRF's own get_object() gives."""

        class PlainView(GenericAPIView):
            queryset = Invoice.objects.all()
            lookup_field = "id"

            def get(self, request, *args, **kwargs):
                return Response({"name": self.get_object().name})

        expected = PlainView.as_view()(rf.get("/"), id=drf)
        response = InvoiceAPIView.as_view()(rf.get("/"), id=ours)
        assert expected.status_code == 404
        assert response.data == expected.data

    def test_200_response(self, rf, invoice):
        response = InvoiceAPIView.as_view()(rf.get("/"), id=invoice.display_id)
        assert response.status_code == 200
        assert response.data == {"name": "Test Invoice"}

    def test_object_permissions_are_checked(self, rf, invoice):
        """DRF's permission classes see the object; a denial is a 403."""

        class DenyAll(permissions.BasePermission):
            def has_object_permission(self, request, view, obj):
                return False

        class View(InvoiceAPIView):
            permission_classes = (DenyAll,)

        response = View.as_view()(rf.get("/"), id=invoice.display_id)
        assert response.status_code == 403


# =============================================================================
# DisplayIDField
# =============================================================================


class PlainSerializer(serializers.Serializer):
    """No Meta.model, so the prefix comes from each instance."""

    display_id = DisplayIDField()
    name = serializers.CharField()


class PlainOptionalSerializer(serializers.Serializer):
    display_id = DisplayIDField(required=False)
    name = serializers.CharField()


class AppCatalogReport:
    """Stand-in for a database-view-backed projection of Product.

    It mirrors Product's uid but is not a Product instance and carries no
    display_id_prefix of its own.
    """

    uuid_field = "uid"

    def __init__(self, uid):
        self.uid = uid
        self.name = "Report Row"


class ProjectionSerializer(serializers.Serializer):
    display_id = DisplayIDField(prefix_from=Product)
    name = serializers.CharField()


@pytest.mark.django_db
class TestDisplayIDField:
    def test_uses_instance_prefix(self, invoice):
        assert PlainSerializer(invoice).data["display_id"] == invoice.display_id

    def test_is_read_only(self):
        assert DisplayIDField().read_only is True

    def test_model_without_prefix_raises(self, order):
        with pytest.raises(ValueError, match="requires a prefix"):
            _ = PlainSerializer(order).data

    def test_prefix_override_uses_model_uuid_field(self, product):
        """prefix= replaces "prod"; the UUID still comes from Product.uid."""

        class Serializer(serializers.Serializer):
            display_id = DisplayIDField(prefix="item")

        data = Serializer(product).data
        assert data["display_id"] == encode_display_id("item", product.uid)

    def test_required_false(self, order, invoice):
        """Returns None instead of raising when there's no prefix."""
        assert PlainOptionalSerializer(order).data["display_id"] is None
        assert PlainOptionalSerializer(invoice).data["display_id"] == invoice.display_id


@pytest.mark.django_db
class TestDisplayIDFieldPrefixFrom:
    def test_projection_uses_referenced_model_prefix(self, product):
        """The projection has no prefix of its own; Product's "prod" is used."""
        data = ProjectionSerializer(AppCatalogReport(uid=product.uid)).data
        assert data["display_id"] == encode_display_id("prod", product.uid)

    def test_wins_over_instance_prefix(self, invoice):
        """invoice has its own "inv" prefix, but prefix_from=Product wins."""
        data = ProjectionSerializer(invoice).data
        assert data["display_id"] == encode_display_id("prod", invoice.id)

    def test_prefix_and_prefix_from_together_raises(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            DisplayIDField(prefix="item", prefix_from=Product)

    def test_model_without_prefix_raises_at_init(self):
        with pytest.raises(ValueError, match="has no display_id_prefix"):
            DisplayIDField(prefix_from=Order)


# =============================================================================
# drf-spectacular schema for DisplayIDField
# =============================================================================


class InvoiceModelSerializer(serializers.ModelSerializer):
    display_id = DisplayIDField()

    class Meta:
        model = Invoice
        fields = ("id", "display_id", "name")


@pytest.mark.django_db
class TestDisplayIDFieldSchema:
    @pytest.fixture(autouse=True)
    def _spectacular(self):
        pytest.importorskip("drf_spectacular")

    def _schema(self, field, view=None):
        from django_display_ids.contrib.drf_spectacular import DisplayIDFieldExtension

        auto_schema = type("AutoSchema", (), {"view": view})() if view else None
        return DisplayIDFieldExtension(target=field).map_serializer_field(
            auto_schema, "response"
        )

    def test_uses_serializer_model_prefix(self):
        schema = self._schema(InvoiceModelSerializer().fields["display_id"])
        assert schema["example"].startswith("inv_")
        assert schema["pattern"] == r"^inv_[0-9A-Za-z]{22}$"
        assert schema["readOnly"] is True

    def test_uses_prefix_override(self):
        class Serializer(serializers.Serializer):
            display_id = DisplayIDField(prefix="item")

        assert self._schema(Serializer().fields["display_id"])["example"].startswith(
            "item_"
        )

    def test_uses_prefix_from(self):
        field = ProjectionSerializer().fields["display_id"]
        assert self._schema(field)["example"].startswith("prod_")

    def test_generic_without_model(self):
        schema = self._schema(PlainSerializer().fields["display_id"])
        assert schema["example"].startswith("type_")
        assert schema["pattern"] == r"^[a-z]{1,16}_[0-9A-Za-z]{22}$"

    def test_falls_back_to_view_queryset(self):
        """A plain serializer on a view gets the prefix from the view's model."""
        field = PlainSerializer().fields["display_id"]

        class ViewWithGetQueryset:
            def get_queryset(self):
                return Invoice.objects.all()

        class ViewWithQuerysetAttr:
            queryset = Invoice.objects.all()

            def get_queryset(self):
                raise RuntimeError("needs a request")

        assert self._schema(field, ViewWithGetQueryset())["example"].startswith("inv_")
        assert self._schema(field, ViewWithQuerysetAttr())["example"].startswith("inv_")

    def test_serializer_prefix_attribute_is_ignored(self):
        """The schema only uses prefix sources the field reads at runtime.

        DisplayIDField doesn't read display_id_prefix from its serializer, so
        the schema mustn't either, or the docs would show inv_... while the
        API raises or outputs something else.
        """

        class Serializer(serializers.Serializer):
            display_id_prefix = "inv"
            display_id = DisplayIDField()

        assert self._schema(Serializer().fields["display_id"])["example"].startswith(
            "type_"
        )


@pytest.mark.parametrize(
    ("prefix", "kwargs", "expected"),
    [
        ("user", {}, "Identifier: display_id (user_xxx), UUID, or slug"),
        ("user", {"with_slug": False}, "Identifier: display_id (user_xxx) or UUID"),
        ("user", {"with_uuid": False}, "Identifier: display_id (user_xxx) or slug"),
        (
            "user",
            {"with_uuid": False, "with_slug": False},
            "Identifier: display_id (user_xxx)",
        ),
        (
            "user",
            {"strategies": ("display_id", "slug")},
            "Identifier: display_id (user_xxx) or slug",
        ),
        ("user", {"strategies": ("uuid",)}, "Identifier: UUID"),
        (None, {}, "Identifier: UUID or slug"),
    ],
)
def test_id_param_description(prefix, kwargs, expected):
    from django_display_ids.contrib.drf_spectacular import id_param_description

    assert id_param_description(prefix, **kwargs) == expected


def test_id_param_description_follows_setting(settings):
    """Without strategies, with_uuid or with_slug, the STRATEGIES setting decides."""
    from django_display_ids.contrib.drf_spectacular import id_param_description

    settings.DISPLAY_IDS = {"STRATEGIES": ("display_id", "uuid")}
    assert id_param_description("user") == "Identifier: display_id (user_xxx) or UUID"


def test_importing_drf_contrib_registers_schema_extensions():
    """The extensions register without importing the drf_spectacular module."""
    pytest.importorskip("drf_spectacular")
    code = (
        "import django; django.setup()\n"
        "import django_display_ids.contrib.rest_framework\n"
        "from drf_spectacular.extensions import (\n"
        "    OpenApiSerializerFieldExtension, OpenApiViewExtension)\n"
        "names = {e.__name__ for e in OpenApiSerializerFieldExtension._registry}\n"
        "names |= {e.__name__ for e in OpenApiViewExtension._registry}\n"
        "print(sorted(n for n in names if 'DisplayID' in n))\n"
    )
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "tests.settings"}
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == (
        "['DisplayIDFieldExtension', 'DisplayIDMixinExtension', "
        "'DisplayIDRelatedFieldExtension']"
    )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("name",)


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("id",)


@pytest.mark.django_db
class TestPathParameterSchema:
    """DisplayIDMixin views document the identifiers get_object() accepts."""

    @pytest.fixture(autouse=True)
    def _spectacular(self, settings):
        pytest.importorskip("drf_spectacular")
        settings.REST_FRAMEWORK = {
            "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"
        }

    def _paths(self, patterns):
        from drf_spectacular.generators import SchemaGenerator

        schema = SchemaGenerator(patterns=patterns).get_schema(public=True)
        return {
            path: ops["get"].get("parameters", [])
            for path, ops in schema["paths"].items()
        }

    def _viewset(self, queryset, serializer, decorator=None, **attrs):
        from rest_framework import viewsets
        from rest_framework.routers import SimpleRouter

        viewset = type(
            "ViewSet",
            (DisplayIDMixin, viewsets.ReadOnlyModelViewSet),
            {"queryset": queryset, "serializer_class": serializer, **attrs},
        )
        if decorator is not None:
            viewset = decorator(viewset)
        router = SimpleRouter()
        router.register("things", viewset, basename="thing")
        return router.urls

    def test_default_strategies(self):
        paths = self._paths(
            self._viewset(Invoice.objects.all(), InvoiceModelSerializer)
        )
        assert paths["/things/"] == []
        # The router's {pk} is renamed {id}; the parameter follows it
        [param] = paths["/things/{id}/"]
        assert param["name"] == "id"
        assert param["description"] == (
            "Identifier: display_id (inv_xxx), UUID, or slug"
        )
        # Not the primary key's format: uuid, which display IDs would fail
        assert param["schema"] == {
            "type": "string",
            "example": example_display_id("inv"),
        }

    def test_display_id_only_has_pattern(self):
        paths = self._paths(
            self._viewset(
                Invoice.objects.all(),
                InvoiceModelSerializer,
                lookup_strategies=("display_id",),
            )
        )
        [param] = paths["/things/{id}/"]
        assert param["description"] == "Identifier: display_id (inv_xxx)"
        assert param["schema"]["pattern"] == r"^inv_[0-9A-Za-z]{22}$"

    def test_uuid_only_has_uuid_format(self):
        paths = self._paths(
            self._viewset(
                Invoice.objects.all(),
                InvoiceModelSerializer,
                lookup_strategies=("uuid",),
            )
        )
        [param] = paths["/things/{id}/"]
        assert param["description"] == "Identifier: UUID"
        assert param["schema"] == {"type": "string", "format": "uuid"}

    def test_model_without_slug_field(self):
        paths = self._paths(self._viewset(Tag.objects.all(), TagSerializer))
        [param] = paths["/things/{id}/"]
        assert param["description"] == "Identifier: display_id (tag_xxx) or UUID"

    def test_model_without_prefix(self):
        paths = self._paths(self._viewset(Order.objects.all(), OrderSerializer))
        [param] = paths["/things/{id}/"]
        assert param["description"] == "Identifier: UUID or slug"
        assert param["schema"] == {"type": "string"}

    def test_custom_lookup_url_kwarg(self):
        from django.urls import path

        class View(DisplayIDMixin, GenericAPIView):
            lookup_url_kwarg = "invoice"
            queryset = Invoice.objects.all()
            serializer_class = InvoiceModelSerializer

            def get(self, request, *args, **kwargs):
                return Response()

        paths = self._paths([path("invoices/<invoice>/", View.as_view())])
        [param] = paths["/invoices/{invoice}/"]
        assert param["description"] == (
            "Identifier: display_id (inv_xxx), UUID, or slug"
        )

    def test_extend_schema_on_class_wins(self):
        from drf_spectacular.utils import OpenApiParameter, extend_schema

        decorator = extend_schema(
            parameters=[
                OpenApiParameter("id", str, OpenApiParameter.PATH, description="Mine")
            ]
        )
        urls = self._viewset(
            Invoice.objects.all(), InvoiceModelSerializer, decorator=decorator
        )
        [param] = self._paths(urls)["/things/{id}/"]
        assert param["description"] == "Mine"

    def test_action_with_its_own_extend_schema(self):
        """An action decorated for something else still gets the parameter."""
        from drf_spectacular.utils import extend_schema
        from rest_framework.decorators import action

        @extend_schema(summary="Fetch")
        def retrieve(self, *args, **kwargs):
            raise NotImplementedError

        @extend_schema(summary="Icon")
        @action(detail=True)
        def icon(self, *args, **kwargs):
            raise NotImplementedError

        original_schema = retrieve.kwargs["schema"]
        paths = self._paths(
            self._viewset(
                Invoice.objects.all(),
                InvoiceModelSerializer,
                retrieve=retrieve,
                icon=icon,
            )
        )
        expected = "Identifier: display_id (inv_xxx), UUID, or slug"
        for path in ("/things/{id}/", "/things/{id}/icon/"):
            [param] = paths[path]
            assert param["description"] == expected, path
        # The view's own methods are left alone
        assert retrieve.kwargs["schema"] is original_schema

    def test_extend_schema_on_method_wins(self):
        from drf_spectacular.utils import OpenApiParameter, extend_schema

        @extend_schema(
            parameters=[
                OpenApiParameter("id", str, OpenApiParameter.PATH, description="Mine")
            ]
        )
        def retrieve(self, *args, **kwargs):
            raise NotImplementedError

        urls = self._viewset(
            Invoice.objects.all(), InvoiceModelSerializer, retrieve=retrieve
        )
        [param] = self._paths(urls)["/things/{id}/"]
        assert param["description"] == "Mine"
