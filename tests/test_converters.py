"""Tests for URL path converters."""

import uuid

import pytest
from django.urls import path, register_converter

from django_display_ids.converters import (
    DisplayIDConverter,
    DisplayIDOrUUIDConverter,
    UUIDConverter,
)
from django_display_ids.encoding import encode_display_id


class TestDisplayIDConverter:
    """Tests for DisplayIDConverter."""

    def test_regex_matches_valid_display_id(self):
        """Regex matches valid display IDs."""
        import re

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
        import re

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


class TestUUIDConverter:
    """Tests for UUIDConverter."""

    def test_regex_matches_hyphenated_uuid(self):
        """Regex matches hyphenated UUIDs."""
        import re

        pattern = re.compile(f"^{UUIDConverter.regex}$")

        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]
        for uuid_str in valid_uuids:
            assert pattern.match(uuid_str), f"Should match: {uuid_str}"

    def test_regex_matches_unhyphenated_uuid(self):
        """Regex matches unhyphenated UUIDs."""
        import re

        pattern = re.compile(f"^{UUIDConverter.regex}$")

        valid_uuids = [
            "550e8400e29b41d4a716446655440000",
            "00000000000000000000000000000000",
            "ffffffffffffffffffffffffffffffff",
        ]
        for uuid_str in valid_uuids:
            assert pattern.match(uuid_str), f"Should match: {uuid_str}"

    def test_regex_rejects_invalid_uuids(self):
        """Regex rejects invalid UUIDs."""
        import re

        pattern = re.compile(f"^{UUIDConverter.regex}$")

        invalid_uuids = [
            "550e8400-e29b-41d4-a716-44665544000",  # too short
            "550e8400-e29b-41d4-a716-4466554400000",  # too long
            "550e8400e29b41d4a71644665544000",  # unhyphenated too short
            "550e8400e29b41d4a7164466554400000",  # unhyphenated too long
            "550e8400-e29b-41d4-a716446655440000",  # missing hyphen
            "GGGGGGGG-GGGG-GGGG-GGGG-GGGGGGGGGGGG",  # invalid hex
            "inv_2aUyqjCzEIiEcYMKj7TZtw",  # display ID
        ]
        for invalid_uuid in invalid_uuids:
            assert not pattern.match(invalid_uuid), f"Should not match: {invalid_uuid}"

    def test_to_python_returns_value(self):
        """to_python returns the value unchanged."""
        converter = UUIDConverter()
        value = "550e8400-e29b-41d4-a716-446655440000"
        assert converter.to_python(value) == value

    def test_to_url_returns_value(self):
        """to_url returns the value unchanged."""
        converter = UUIDConverter()
        value = "550e8400-e29b-41d4-a716-446655440000"
        assert converter.to_url(value) == value


class TestDisplayIDOrUUIDConverter:
    """Tests for DisplayIDOrUUIDConverter."""

    def test_regex_matches_display_id(self):
        """Regex matches display IDs."""
        import re

        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        valid_ids = [
            "inv_0000000000000000000000",
            "prod_2aUyqjCzEIiEcYMKj7TZtw",
        ]
        for display_id in valid_ids:
            assert pattern.match(display_id), f"Should match: {display_id}"

    def test_regex_matches_hyphenated_uuid(self):
        """Regex matches hyphenated UUIDs."""
        import re

        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        assert pattern.match("550e8400-e29b-41d4-a716-446655440000")

    def test_regex_matches_unhyphenated_uuid(self):
        """Regex matches unhyphenated UUIDs."""
        import re

        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        assert pattern.match("550e8400e29b41d4a716446655440000")

    def test_regex_rejects_invalid(self):
        """Regex rejects invalid identifiers."""
        import re

        pattern = re.compile(f"^{DisplayIDOrUUIDConverter.regex}$")

        invalid = [
            "INV_0000000000000000000000",  # uppercase prefix
            "not-a-valid-id",
            "random-string",
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


def _register_converters_once():
    """Register converters once at module load time."""
    from django.urls.converters import REGISTERED_CONVERTERS

    if "display_id" not in REGISTERED_CONVERTERS:
        register_converter(DisplayIDConverter, "display_id")
    if "did_uuid" not in REGISTERED_CONVERTERS:
        register_converter(UUIDConverter, "did_uuid")
    if "display_id_or_uuid" not in REGISTERED_CONVERTERS:
        register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")


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

    def test_uuid_route_matches_hyphenated(self):
        """UUID route matches hyphenated UUIDs."""
        from django.urls import resolve

        urlpatterns = [
            path("invoices/<did_uuid:id>/", lambda _r, _id: None),
        ]

        match = resolve(
            "/invoices/550e8400-e29b-41d4-a716-446655440000/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_uuid_route_matches_unhyphenated(self):
        """UUID route matches unhyphenated UUIDs."""
        from django.urls import resolve

        urlpatterns = [
            path("invoices/<did_uuid:id>/", lambda _r, _id: None),
        ]

        match = resolve(
            "/invoices/550e8400e29b41d4a716446655440000/",
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert match.kwargs["id"] == "550e8400e29b41d4a716446655440000"

    def test_uuid_route_rejects_display_id(self):
        """UUID route rejects display IDs."""
        from django.urls import Resolver404, resolve

        urlpatterns = [
            path("invoices/<did_uuid:id>/", lambda _r, _id: None),
        ]

        with pytest.raises(Resolver404):
            resolve(
                "/invoices/inv_2aUyqjCzEIiEcYMKj7TZtw/",
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

    def test_reverse_uuid(self):
        """reverse() works with UUID converter."""
        from django.urls import reverse

        urlpatterns = [
            path("invoices/<did_uuid:id>/", lambda _r, _id: None, name="invoice"),
        ]

        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        url = reverse(
            "invoice",
            kwargs={"id": uuid_str},
            urlconf=type("urls", (), {"urlpatterns": urlpatterns}),
        )
        assert url == f"/invoices/{uuid_str}/"
