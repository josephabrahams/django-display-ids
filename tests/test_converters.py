"""Tests for URL path converters."""

import re
import uuid

import pytest
from django.urls import path, register_converter

from django_display_ids.converters import (
    DISPLAY_ID_REGEX,
    SLUG_REGEX,
    DisplayIDConverter,
    DisplayIDOrSlugConverter,
    DisplayIDOrUUIDConverter,
    DisplayIDOrUUIDOrSlugConverter,
    make_display_id_or_slug_converter,
    make_display_id_or_uuid_or_slug_converter,
)
from django_display_ids.encoding import encode_display_id


class TestDisplayIDConverter:
    """Tests for DisplayIDConverter."""

    def test_regex_matches_valid_display_id(self):
        """Regex matches valid display IDs."""
        pattern = re.compile(f"^{DisplayIDConverter.regex}$")

        valid_ids = [
            "inv_0000000000000000000000",
            "a_0123456789ABCDEFabcdef",
            "abcdefghijklmnop_zzzzzzzzzzzzzzzzzzzzzz",
            "prod_2aUyqjCzEIiEcYMKj7TZtw",
        ]
        for display_id in valid_ids:
            assert pattern.match(display_id), f"Should match: {display_id}"

    def test_regex_rejects_invalid_display_ids(self):
        """Regex rejects invalid display IDs."""
        pattern = re.compile(f"^{DisplayIDConverter.regex}$")

        invalid_ids = [
            "INV_0000000000000000000000",  # uppercase prefix
            "inv_000000000000000000000",  # 21 chars (too short)
            "inv_00000000000000000000000",  # 23 chars (too long)
            "inv-0000000000000000000000",  # hyphen instead of underscore
            "1nv_0000000000000000000000",  # prefix starts with number
            "_0000000000000000000000",  # empty prefix
            "inv_",  # empty base62
            "550e8400-e29b-41d4-a716-446655440000",  # UUID
        ]
        for invalid_id in invalid_ids:
            assert not pattern.match(invalid_id), f"Should not match: {invalid_id}"

    def test_to_python_returns_value(self):
        """to_python returns the value unchanged."""
        converter = DisplayIDConverter()
        value = "inv_2aUyqjCzEIiEcYMKj7TZtw"
        assert converter.to_python(value) == value

    def test_to_url_returns_value(self):
        """to_url returns the value unchanged."""
        converter = DisplayIDConverter()
        value = "inv_2aUyqjCzEIiEcYMKj7TZtw"
        assert converter.to_url(value) == value

    def test_uses_display_id_regex_constant(self):
        """Converter uses the DISPLAY_ID_REGEX constant."""
        assert DisplayIDConverter.regex == DISPLAY_ID_REGEX


class TestDisplayIDOrUUIDConverter:
    """Tests for DisplayIDOrUUIDConverter."""

    def test_regex_matches_display_id(self):
        """Regex matches display IDs."""
        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        valid_ids = [
            "inv_0000000000000000000000",
            "prod_2aUyqjCzEIiEcYMKj7TZtw",
        ]
        for display_id in valid_ids:
            assert pattern.match(display_id), f"Should match: {display_id}"

    def test_regex_matches_hyphenated_uuid(self):
        """Regex matches hyphenated UUIDs."""
        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        assert pattern.match("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.parametrize(
        "value",
        [
            "550e8400-e29b-41d4-a716-446655440000",
            "550E8400-E29B-41D4-A716-446655440000",
            "550e8400e29b41d4a716446655440000",
            "550E8400E29B41D4A716446655440000",
        ],
    )
    def test_regex_matches_all_uuid_forms(self, value):
        """Regex matches UUIDs with or without hyphens, in any case."""
        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        assert pattern.match(value)

    def test_regex_rejects_invalid(self):
        """Regex rejects invalid identifiers."""
        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        invalid = [
            "INV_0000000000000000000000",  # uppercase prefix
            "550e8400e29b-41d4-a716-446655440000",  # partly hyphenated
            "550e8400-e29b-41d4-a716-44665544000",  # too short
            "550e8400-e29b-41d4-a716-44665544000g",  # not hex
        ]
        for invalid_id in invalid:
            assert not pattern.match(invalid_id), f"Should not match: {invalid_id}"

    def test_to_python_returns_value(self):
        """to_python returns the value unchanged."""
        converter = DisplayIDOrUUIDConverter()
        value = "inv_2aUyqjCzEIiEcYMKj7TZtw"
        assert converter.to_python(value) == value

    def test_to_url_returns_value(self):
        """to_url returns the value unchanged."""
        converter = DisplayIDOrUUIDConverter()
        value = "inv_2aUyqjCzEIiEcYMKj7TZtw"
        assert converter.to_url(value) == value


class TestDisplayIDOrSlugConverter:
    """Tests for DisplayIDOrSlugConverter."""

    def test_regex_matches_display_id(self):
        """Regex matches display IDs."""
        pattern = re.compile(f"^{DisplayIDOrSlugConverter.regex}$")

        valid_ids = [
            "inv_0000000000000000000000",
            "prod_2aUyqjCzEIiEcYMKj7TZtw",
        ]
        for display_id in valid_ids:
            assert pattern.match(display_id), f"Should match: {display_id}"

    def test_regex_matches_slug(self):
        """Regex matches slugs."""
        pattern = re.compile(f"^{DisplayIDOrSlugConverter.regex}$")

        valid_slugs = [
            "my-product",
            "my_product",
            "MyProduct",
            "product-123",
            "PRODUCT",
            "a",
        ]
        for slug in valid_slugs:
            assert pattern.match(slug), f"Should match: {slug}"

    def test_regex_rejects_uuid(self):
        """Regex does not match UUIDs (they match as slugs partially)."""
        pattern = re.compile(f"^{DisplayIDOrSlugConverter.regex}$")

        # Hyphenated UUID matches because hyphens and alphanumerics are valid slug chars
        assert pattern.match("550e8400-e29b-41d4-a716-446655440000")

        # Unhyphenated UUID also matches as a slug
        assert pattern.match("550e8400e29b41d4a716446655440000")

    def test_regex_rejects_invalid(self):
        """Regex rejects truly invalid identifiers."""
        pattern = re.compile(f"^{DisplayIDOrSlugConverter.regex}$")

        invalid = [
            "",  # empty
            "product slug",  # space
            "product/slug",  # slash
            "product.slug",  # dot
        ]
        for invalid_id in invalid:
            assert not pattern.match(invalid_id), f"Should not match: {invalid_id}"

    def test_to_python_returns_value(self):
        """to_python returns the value unchanged."""
        converter = DisplayIDOrSlugConverter()
        value = "my-product"
        assert converter.to_python(value) == value

    def test_to_url_returns_value(self):
        """to_url returns the value unchanged."""
        converter = DisplayIDOrSlugConverter()
        value = "my-product"
        assert converter.to_url(value) == value


class TestDisplayIDOrUUIDOrSlugConverter:
    """Tests for DisplayIDOrUUIDOrSlugConverter."""

    def test_regex_matches_display_id(self):
        """Regex matches display IDs."""
        pattern = re.compile(f"^{DisplayIDOrUUIDOrSlugConverter.regex}$")

        valid_ids = [
            "inv_0000000000000000000000",
            "prod_2aUyqjCzEIiEcYMKj7TZtw",
        ]
        for display_id in valid_ids:
            assert pattern.match(display_id), f"Should match: {display_id}"

    def test_regex_matches_hyphenated_uuid(self):
        """Regex matches hyphenated UUIDs."""
        pattern = re.compile(f"^{DisplayIDOrUUIDOrSlugConverter.regex}$")

        assert pattern.match("550e8400-e29b-41d4-a716-446655440000")

    def test_regex_matches_unhyphenated_uppercase_uuid(self):
        """Regex matches UUIDs without hyphens, in any case."""
        pattern = re.compile(f"^{DisplayIDOrUUIDOrSlugConverter.regex}$")

        assert pattern.match("550E8400E29B41D4A716446655440000")

    def test_regex_matches_slug(self):
        """Regex matches slugs."""
        pattern = re.compile(f"^{DisplayIDOrUUIDOrSlugConverter.regex}$")

        valid_slugs = [
            "my-product",
            "my_product",
            "MyProduct",
            "product-123",
        ]
        for slug in valid_slugs:
            assert pattern.match(slug), f"Should match: {slug}"

    def test_regex_rejects_invalid(self):
        """Regex rejects invalid identifiers."""
        pattern = re.compile(f"^{DisplayIDOrUUIDOrSlugConverter.regex}$")

        invalid = [
            "",  # empty
            "product slug",  # space
            "product/slug",  # slash
        ]
        for invalid_id in invalid:
            assert not pattern.match(invalid_id), f"Should not match: {invalid_id}"

    def test_to_python_returns_value(self):
        """to_python returns the value unchanged."""
        converter = DisplayIDOrUUIDOrSlugConverter()
        value = "my-product"
        assert converter.to_python(value) == value

    def test_to_url_returns_value(self):
        """to_url returns the value unchanged."""
        converter = DisplayIDOrUUIDOrSlugConverter()
        value = "my-product"
        assert converter.to_url(value) == value


class TestMakeDisplayIDOrSlugConverter:
    """Tests for make_display_id_or_slug_converter factory."""

    def test_default_uses_slug_regex(self):
        """Default converter uses SLUG_REGEX."""
        converter_class = make_display_id_or_slug_converter()
        # Should contain the default slug pattern
        assert (
            SLUG_REGEX in converter_class.regex
            or "[-a-zA-Z0-9_]+" in converter_class.regex
        )

    def test_custom_regex(self):
        """Custom regex is used in converter."""
        custom_regex = r"[a-z0-9-]+"
        converter_class = make_display_id_or_slug_converter(custom_regex)

        pattern = re.compile(f"^{converter_class.regex}$")

        # Should match display ID
        assert pattern.match("inv_0000000000000000000000")

        # Should match lowercase slug
        assert pattern.match("my-product")

        # Should NOT match uppercase (custom regex is lowercase only)
        assert not pattern.match("MY-PRODUCT")

    def test_returns_subclass(self):
        """Factory returns a subclass of DisplayIDOrSlugConverter."""
        converter_class = make_display_id_or_slug_converter()
        assert issubclass(converter_class, DisplayIDOrSlugConverter)

    def test_converter_methods_work(self):
        """Converter methods work correctly."""
        converter_class = make_display_id_or_slug_converter()
        converter = converter_class()
        assert converter.to_python("test") == "test"
        assert converter.to_url("test") == "test"


class TestMakeDisplayIDOrUUIDOrSlugConverter:
    """Tests for make_display_id_or_uuid_or_slug_converter factory."""

    def test_default_uses_slug_regex(self):
        """Default converter uses SLUG_REGEX."""
        converter_class = make_display_id_or_uuid_or_slug_converter()
        # Should contain the default slug pattern
        assert (
            SLUG_REGEX in converter_class.regex
            or "[-a-zA-Z0-9_]+" in converter_class.regex
        )

    def test_custom_regex(self):
        """Custom regex is used in converter."""
        custom_regex = r"[a-z0-9-]+"
        converter_class = make_display_id_or_uuid_or_slug_converter(custom_regex)

        pattern = re.compile(f"^{converter_class.regex}$")

        # Should match display ID
        assert pattern.match("inv_0000000000000000000000")

        # Should match UUID
        assert pattern.match("550e8400-e29b-41d4-a716-446655440000")

        # Should match lowercase slug
        assert pattern.match("my-product")

        # Should NOT match uppercase slug (custom regex is lowercase only)
        assert not pattern.match("MY-PRODUCT")

    def test_returns_subclass(self):
        """Factory returns a subclass of DisplayIDOrUUIDOrSlugConverter."""
        converter_class = make_display_id_or_uuid_or_slug_converter()
        assert issubclass(converter_class, DisplayIDOrUUIDOrSlugConverter)

    def test_converter_methods_work(self):
        """Converter methods work correctly."""
        converter_class = make_display_id_or_uuid_or_slug_converter()
        converter = converter_class()
        assert converter.to_python("test") == "test"
        assert converter.to_url("test") == "test"


def _register_converters_once():
    """Register converters once at module load time."""
    from django.urls.converters import REGISTERED_CONVERTERS

    if "display_id" not in REGISTERED_CONVERTERS:
        register_converter(DisplayIDConverter, "display_id")
    if "display_id_or_uuid" not in REGISTERED_CONVERTERS:
        register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")
    if "display_id_or_slug" not in REGISTERED_CONVERTERS:
        register_converter(DisplayIDOrSlugConverter, "display_id_or_slug")
    if "identifier" not in REGISTERED_CONVERTERS:
        register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")


_register_converters_once()


class TestConverterRouting:
    """Integration tests for converter routing."""

    def test_display_id_route_resolves(self):
        """Display ID route resolves valid display IDs."""
        from django.urls import resolve

        urlpatterns = [
            path("invoices/<display_id:id>/", lambda _r, _id: None, name="invoice"),
        ]

        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        # Use resolve with urlconf parameter
        match = resolve(
            f"/invoices/{display_id}/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == display_id

    def test_display_id_route_rejects_uuid(self):
        """Display ID route rejects UUIDs."""
        from django.urls import Resolver404, resolve

        urlpatterns = [
            path("invoices/<display_id:id>/", lambda _r, _id: None),
        ]

        with pytest.raises(Resolver404):
            resolve(
                "/invoices/550e8400-e29b-41d4-a716-446655440000/",
                urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
            )

    def test_either_route_matches_display_id(self):
        """Either route matches display IDs."""
        from django.urls import resolve

        urlpatterns = [
            path("invoices/<display_id_or_uuid:id>/", lambda _r, _id: None),
        ]

        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        match = resolve(
            f"/invoices/{display_id}/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == display_id

    def test_either_route_matches_uuid(self):
        """Either route matches UUIDs."""
        from django.urls import resolve

        urlpatterns = [
            path("invoices/<display_id_or_uuid:id>/", lambda _r, _id: None),
        ]

        match = resolve(
            "/invoices/550e8400-e29b-41d4-a716-446655440000/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_display_id_or_slug_matches_display_id(self):
        """DisplayIDOrSlug route matches display IDs."""
        from django.urls import resolve

        urlpatterns = [
            path("products/<display_id_or_slug:id>/", lambda _r, _id: None),
        ]

        test_uuid = uuid.uuid4()
        display_id = encode_display_id("prod", test_uuid)

        match = resolve(
            f"/products/{display_id}/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == display_id

    def test_display_id_or_slug_matches_slug(self):
        """DisplayIDOrSlug route matches slugs."""
        from django.urls import resolve

        urlpatterns = [
            path("products/<display_id_or_slug:id>/", lambda _r, _id: None),
        ]

        match = resolve(
            "/products/my-awesome-product/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == "my-awesome-product"

    def test_identifier_matches_all_formats(self):
        """Identifier route matches display ID, UUID, and slug."""
        from django.urls import resolve

        urlpatterns = [
            path("items/<identifier:id>/", lambda _r, _id: None),
        ]

        # Display ID
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("item", test_uuid)
        match = resolve(
            f"/items/{display_id}/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == display_id

        # UUID
        match = resolve(
            "/items/550e8400-e29b-41d4-a716-446655440000/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == "550e8400-e29b-41d4-a716-446655440000"

        # Slug
        match = resolve(
            "/items/my-item-slug/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == "my-item-slug"

    def test_reverse_display_id(self):
        """reverse() works with display ID converter."""
        from django.urls import reverse

        urlpatterns = [
            path("invoices/<display_id:id>/", lambda _r, _id: None, name="invoice"),
        ]

        display_id = "inv_2aUyqjCzEIiEcYMKj7TZtw"
        url = reverse(
            "invoice",
            kwargs={"id": display_id},
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert url == f"/invoices/{display_id}/"

    def test_reverse_identifier(self):
        """reverse() works with identifier converter."""
        from django.urls import reverse

        urlpatterns = [
            path("items/<identifier:id>/", lambda _r, _id: None, name="item"),
        ]

        # Works with display ID
        display_id = "item_2aUyqjCzEIiEcYMKj7TZtw"
        url = reverse(
            "item",
            kwargs={"id": display_id},
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert url == f"/items/{display_id}/"

        # Works with slug
        slug = "my-item"
        url = reverse(
            "item",
            kwargs={"id": slug},
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert url == f"/items/{slug}/"


class TestUUIDObjects:
    """Converters accept uuid.UUID objects in reverse(), like Django's <uuid:>."""

    @pytest.mark.parametrize(
        "converter",
        [
            DisplayIDConverter,
            DisplayIDOrUUIDConverter,
            DisplayIDOrSlugConverter,
            DisplayIDOrUUIDOrSlugConverter,
        ],
    )
    def test_to_url_stringifies_uuid(self, converter):
        value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert converter().to_url(value) == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.parametrize("name", ["display_id_or_uuid", "identifier"])
    def test_reverse_with_uuid_object(self, name):
        from django.urls import reverse

        urlpatterns = [path(f"items/<{name}:id>/", lambda _r, _id: None, name="item")]
        value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

        url = reverse(
            "item",
            kwargs={"id": value},
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert url == f"/items/{value}/"

    def test_reverse_display_id_rejects_uuid_object(self):
        """<display_id:> can't build a URL from a bare UUID (no prefix)."""
        from django.urls import NoReverseMatch, reverse

        urlpatterns = [
            path("items/<display_id:id>/", lambda _r, _id: None, name="item")
        ]

        with pytest.raises(NoReverseMatch):
            reverse(
                "item",
                kwargs={"id": uuid.uuid4()},
                urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
            )

    def test_uuid_regex_builds_on_django(self):
        """The UUID pattern reuses Django's <uuid:> pattern."""
        from django.urls.converters import UUIDConverter

        from django_display_ids.converters import UUID_REGEX

        assert UUIDConverter.regex in UUID_REGEX

    @pytest.mark.parametrize(
        "value",
        [
            "8c2b67fc-0fff-4c46-a3b3-e30d1829a559",
            "8C2B67FC-0FFF-4C46-A3B3-E30D1829A559",
            "8c2b67fc0fff4c46a3b3e30d1829a559",
            "8C2B67FC0FFF4C46A3B3E30D1829A559",
        ],
    )
    @pytest.mark.parametrize("name", ["display_id_or_uuid", "identifier"])
    def test_all_uuid_forms_route_and_reverse(self, name, value):
        from django.urls import resolve, reverse

        urlpatterns = [path(f"items/<{name}:id>/", lambda _r, _id: None, name="item")]
        urlconf = type("urls", (), {"urlpatterns": urlpatterns})

        assert resolve(f"/items/{value}/", urlconf=urlconf).kwargs["id"] == value
        url = reverse("item", kwargs={"id": value}, urlconf=urlconf)
        assert url == f"/items/{value}/"


class TestSlugRegexSetting:
    """The default slug converters read SLUG_REGEX when the URLconf is built."""

    def test_class_regex_follows_setting(self, settings):
        settings.DISPLAY_IDS = {"SLUG_REGEX": r"[a-z]+"}
        assert DisplayIDOrSlugConverter.regex.endswith("|[a-z]+)")
        assert DisplayIDOrUUIDOrSlugConverter.regex.endswith("|[a-z]+)")

    def test_route_follows_setting(self, settings):
        from django.urls import Resolver404, resolve

        settings.DISPLAY_IDS = {"SLUG_REGEX": r"[a-z]+"}
        urlpatterns = [path("p/<display_id_or_slug:id>/", lambda _r, _id: None)]
        urlconf = type("urls", (), {"urlpatterns": urlpatterns})

        assert resolve("/p/lowercase/", urlconf=urlconf).kwargs["id"] == "lowercase"
        with pytest.raises(Resolver404):
            resolve("/p/Has-Caps-1/", urlconf=urlconf)
