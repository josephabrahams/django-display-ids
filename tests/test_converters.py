"""Tests for URL path converters."""

import re
import uuid

import pytest
from django.urls import (
    NoReverseMatch,
    Resolver404,
    path,
    register_converter,
    resolve,
    reverse,
)
from django.urls.converters import REGISTERED_CONVERTERS, UUIDConverter

from django_display_ids.converters import (
    DISPLAY_ID_REGEX,
    UUID_REGEX,
    DisplayIDConverter,
    DisplayIDOrSlugConverter,
    DisplayIDOrUUIDConverter,
    DisplayIDOrUUIDOrSlugConverter,
    make_display_id_or_slug_converter,
    make_display_id_or_uuid_or_slug_converter,
)

CONVERTERS = {
    "display_id": DisplayIDConverter,
    "display_id_or_uuid": DisplayIDOrUUIDConverter,
    "display_id_or_slug": DisplayIDOrSlugConverter,
    "identifier": DisplayIDOrUUIDOrSlugConverter,
}
for _name, _converter in CONVERTERS.items():
    if _name not in REGISTERED_CONVERTERS:
        register_converter(_converter, _name)

DISPLAY_ID = "inv_2aUyqjCzEIiEcYMKj7TZtw"
UUID_FORMS = [
    "550e8400-e29b-41d4-a716-446655440000",
    "550E8400-E29B-41D4-A716-446655440000",
]
# Not UUIDs: only the hyphenated form is, so these can't be mistaken for slugs
NOT_UUID_FORMS = [
    "550e8400e29b41d4a716446655440000",
    "550E8400E29B41D4A716446655440000",
    "550e8400e29b-41d4-a716-446655440000",
]


def _matches(converter, value):
    return re.fullmatch(converter.regex, value) is not None


def _urlconf(route):
    """A throwaway URLconf with one route named "item"."""
    urlpatterns = [path(route, lambda _r, _id: None, name="item")]
    return type("urls", (), {"urlpatterns": urlpatterns})


class TestDisplayIDConverter:
    @pytest.mark.parametrize(
        "value",
        [
            "inv_0000000000000000000000",
            "a_0123456789ABCDEFabcdef",
            "abcdefghijklmnop_zzzzzzzzzzzzzzzzzzzzzz",  # 16-letter prefix
            DISPLAY_ID,
        ],
    )
    def test_matches(self, value):
        assert _matches(DisplayIDConverter, value)

    @pytest.mark.parametrize(
        "value",
        [
            "INV_0000000000000000000000",  # uppercase prefix
            "inv_000000000000000000000",  # 21 characters
            "inv_00000000000000000000000",  # 23 characters
            "inv-0000000000000000000000",  # hyphen instead of underscore
            "1nv_0000000000000000000000",  # digit in prefix
            "_0000000000000000000000",  # no prefix
            "inv_",
            *UUID_FORMS,
        ],
    )
    def test_rejects(self, value):
        assert not _matches(DisplayIDConverter, value)

    def test_uses_shared_pattern(self):
        assert DisplayIDConverter.regex == DISPLAY_ID_REGEX


class TestDisplayIDOrUUIDConverter:
    @pytest.mark.parametrize("value", [DISPLAY_ID, *UUID_FORMS])
    def test_matches(self, value):
        assert _matches(DisplayIDOrUUIDConverter, value)

    @pytest.mark.parametrize(
        "value",
        [
            "INV_0000000000000000000000",  # uppercase prefix stays rejected
            *NOT_UUID_FORMS,
            "550e8400-e29b-41d4-a716-44665544000",  # too short
            "550e8400-e29b-41d4-a716-44665544000g",  # not hex
            "my-slug",
        ],
    )
    def test_rejects(self, value):
        assert not _matches(DisplayIDOrUUIDConverter, value)

    def test_uuid_pattern_builds_on_django(self):
        assert UUIDConverter.regex in UUID_REGEX


class TestDisplayIDOrSlugConverter:
    @pytest.mark.parametrize(
        "value",
        [DISPLAY_ID, "my-product", "my_product", "MyProduct", "PRODUCT", "a"],
    )
    def test_matches(self, value):
        assert _matches(DisplayIDOrSlugConverter, value)

    def test_matches_uuid_as_slug(self):
        """UUIDs match through the slug pattern, not a UUID pattern."""
        assert _matches(DisplayIDOrSlugConverter, UUID_FORMS[0])

    @pytest.mark.parametrize(
        "value", ["", "product slug", "product/slug", "product.slug"]
    )
    def test_rejects(self, value):
        assert not _matches(DisplayIDOrSlugConverter, value)


class TestDisplayIDOrUUIDOrSlugConverter:
    @pytest.mark.parametrize(
        "value", [DISPLAY_ID, *UUID_FORMS, "my-product", "my_product", "MyProduct"]
    )
    def test_matches(self, value):
        assert _matches(DisplayIDOrUUIDOrSlugConverter, value)

    @pytest.mark.parametrize("value", ["", "product slug", "product/slug"])
    def test_rejects(self, value):
        assert not _matches(DisplayIDOrUUIDOrSlugConverter, value)


@pytest.mark.parametrize("converter", CONVERTERS.values())
class TestConversion:
    def test_to_python_passes_value_through(self, converter):
        assert converter().to_python("some-value") == "some-value"

    def test_to_url_stringifies(self, converter):
        """Like Django's <uuid:>, so reverse() accepts UUID objects."""
        value = uuid.UUID(UUID_FORMS[0])
        assert converter().to_url(value) == UUID_FORMS[0]
        assert converter().to_url("some-value") == "some-value"


@pytest.mark.parametrize(
    ("factory", "base", "accepts_uuid"),
    [
        (make_display_id_or_slug_converter, DisplayIDOrSlugConverter, False),
        (
            make_display_id_or_uuid_or_slug_converter,
            DisplayIDOrUUIDOrSlugConverter,
            True,
        ),
    ],
)
class TestConverterFactories:
    def test_returns_subclass(self, factory, base, accepts_uuid):
        assert issubclass(factory(), base)

    def test_custom_regex(self, factory, base, accepts_uuid):
        converter = factory(r"[a-z0-9-]+")
        assert _matches(converter, DISPLAY_ID)
        assert _matches(converter, "my-product")
        assert not _matches(converter, "MY-PRODUCT")
        # "0000...": all digits, so it only matches through the UUID pattern
        assert (
            _matches(converter, "00000000-0000-0000-0000-00000000000A") is accepts_uuid
        )

    def test_custom_regex_ignores_setting(self, factory, base, accepts_uuid, settings):
        converter = factory(r"[a-z]+")
        settings.DISPLAY_IDS = {"SLUG_REGEX": r"[0-9]+"}
        assert _matches(converter, "abc")
        assert not _matches(converter, "123")

    def test_default_follows_setting(self, factory, base, accepts_uuid, settings):
        """Without a custom regex, SLUG_REGEX is read when the URLconf is built."""
        converter = factory()
        settings.DISPLAY_IDS = {"SLUG_REGEX": r"[a-z]+"}
        assert converter.regex.endswith("|[a-z]+)")


class TestDefaultConvertersFollowSetting:
    def test_class_regex(self, settings):
        settings.DISPLAY_IDS = {"SLUG_REGEX": r"[a-z]+"}
        assert DisplayIDOrSlugConverter.regex.endswith("|[a-z]+)")
        assert DisplayIDOrUUIDOrSlugConverter.regex.endswith("|[a-z]+)")

    def test_route(self, settings):
        settings.DISPLAY_IDS = {"SLUG_REGEX": r"[a-z]+"}
        urlconf = _urlconf("p/<display_id_or_slug:id>/")
        assert resolve("/p/lowercase/", urlconf=urlconf).kwargs["id"] == "lowercase"
        with pytest.raises(Resolver404):
            resolve("/p/Has-Caps-1/", urlconf=urlconf)


class TestRouting:
    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("display_id", DISPLAY_ID),
            ("display_id_or_uuid", DISPLAY_ID),
            ("display_id_or_slug", DISPLAY_ID),
            ("display_id_or_slug", "my-awesome-product"),
            ("identifier", DISPLAY_ID),
            ("identifier", "my-item-slug"),
            *[("display_id_or_uuid", v) for v in UUID_FORMS],
            *[("identifier", v) for v in UUID_FORMS],
        ],
    )
    def test_resolve_and_reverse(self, name, value):
        urlconf = _urlconf(f"items/<{name}:id>/")
        assert resolve(f"/items/{value}/", urlconf=urlconf).kwargs["id"] == value
        assert (
            reverse("item", kwargs={"id": value}, urlconf=urlconf) == f"/items/{value}/"
        )

    def test_display_id_route_rejects_uuid(self):
        with pytest.raises(Resolver404):
            resolve(
                f"/items/{UUID_FORMS[0]}/", urlconf=_urlconf("items/<display_id:id>/")
            )

    @pytest.mark.parametrize("name", ["display_id_or_uuid", "identifier"])
    def test_reverse_with_uuid_object(self, name):
        value = uuid.UUID(UUID_FORMS[0])
        url = reverse(
            "item", kwargs={"id": value}, urlconf=_urlconf(f"items/<{name}:id>/")
        )
        assert url == f"/items/{value}/"

    def test_reverse_display_id_rejects_uuid_object(self):
        """<display_id:> can't build a URL from a bare UUID; it has no prefix."""
        with pytest.raises(NoReverseMatch):
            reverse(
                "item",
                kwargs={"id": uuid.uuid4()},
                urlconf=_urlconf("items/<display_id:id>/"),
            )
