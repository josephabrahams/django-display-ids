"""Django URL path converters for display IDs and UUIDs."""

from __future__ import annotations

from .conf import SLUG_REGEX, get_setting

__all__ = [
    "DISPLAY_ID_REGEX",
    "SLUG_REGEX",
    "DisplayIDConverter",
    "DisplayIDOrSlugConverter",
    "DisplayIDOrUUIDConverter",
    "DisplayIDOrUUIDOrSlugConverter",
    "make_display_id_or_slug_converter",
    "make_display_id_or_uuid_or_slug_converter",
]

# Regex pattern constants
DISPLAY_ID_REGEX = r"[a-z]{1,16}_[0-9A-Za-z]{22}"
UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# Slug regex from settings (respects DISPLAY_IDS["SLUG_REGEX"] Django setting)
_SLUG_REGEX: str = str(get_setting("SLUG_REGEX"))


class BaseConverter:
    """Base class for URL path converters with pass-through conversion."""

    def to_python(self, value: str) -> str:
        """Convert the URL value to a Python object."""
        return value

    def to_url(self, value: str) -> str:
        """Convert a Python object to a URL string."""
        return value


class DisplayIDConverter(BaseConverter):
    """Path converter for display IDs.

    Matches the format: {prefix}_{base62} where prefix is 1-16 lowercase
    letters and base62 is exactly 22 alphanumeric characters.

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import DisplayIDConverter

        register_converter(DisplayIDConverter, "display_id")

        urlpatterns = [
            path("invoices/<display_id:id>/", InvoiceDetailView.as_view()),
        ]
    """

    regex = DISPLAY_ID_REGEX


class DisplayIDOrUUIDConverter(BaseConverter):
    """Path converter for display IDs or UUIDs.

    Matches either format:
    - Display ID: {prefix}_{base62}
    - UUID: hyphenated (e.g., 550e8400-e29b-41d4-a716-446655440000)

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import DisplayIDOrUUIDConverter

        register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")

        urlpatterns = [
            path("invoices/<display_id_or_uuid:id>/", InvoiceDetailView.as_view()),
        ]
    """

    regex = rf"(?:{DISPLAY_ID_REGEX}|{UUID_REGEX})"


class DisplayIDOrSlugConverter(BaseConverter):
    """Path converter for display IDs or slugs.

    Matches either format:
    - Display ID: {prefix}_{base62}
    - Slug: matches DISPLAY_IDS["SLUG_REGEX"] setting (default: [-a-zA-Z0-9_]+)

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import DisplayIDOrSlugConverter

        register_converter(DisplayIDOrSlugConverter, "display_id_or_slug")

        urlpatterns = [
            path("products/<display_id_or_slug:id>/", ProductDetailView.as_view()),
        ]
    """

    regex = rf"(?:{DISPLAY_ID_REGEX}|{_SLUG_REGEX})"


class DisplayIDOrUUIDOrSlugConverter(BaseConverter):
    """Path converter for display IDs, UUIDs, or slugs.

    Matches any of:
    - Display ID: {prefix}_{base62}
    - UUID: hyphenated (e.g., 550e8400-e29b-41d4-a716-446655440000)
    - Slug: matches DISPLAY_IDS["SLUG_REGEX"] setting (default: [-a-zA-Z0-9_]+)

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import DisplayIDOrUUIDOrSlugConverter

        register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

        urlpatterns = [
            path("products/<identifier:id>/", ProductDetailView.as_view()),
        ]
    """

    regex = rf"(?:{DISPLAY_ID_REGEX}|{UUID_REGEX}|{_SLUG_REGEX})"


def make_display_id_or_slug_converter(
    slug_regex: str | None = None,
) -> type[DisplayIDOrSlugConverter]:
    """Create a DisplayIDOrSlugConverter with a custom slug regex.

    Args:
        slug_regex: Custom slug regex pattern. If None, uses the
            DISPLAY_IDS["SLUG_REGEX"] setting (defaults to Django's pattern).

    Returns:
        A DisplayIDOrSlugConverter subclass with the custom regex.

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import make_display_id_or_slug_converter

        # Lowercase slugs only
        LowercaseConverter = make_display_id_or_slug_converter(r"[a-z0-9-]+")
        register_converter(LowercaseConverter, "display_id_or_slug")

        urlpatterns = [
            path("products/<display_id_or_slug:id>/", ProductDetailView.as_view()),
        ]
    """
    pattern = slug_regex if slug_regex is not None else get_setting("SLUG_REGEX")

    class CustomDisplayIDOrSlugConverter(DisplayIDOrSlugConverter):
        regex = rf"(?:{DISPLAY_ID_REGEX}|{pattern})"

    return CustomDisplayIDOrSlugConverter


def make_display_id_or_uuid_or_slug_converter(
    slug_regex: str | None = None,
) -> type[DisplayIDOrUUIDOrSlugConverter]:
    """Create a DisplayIDOrUUIDOrSlugConverter with a custom slug regex.

    Args:
        slug_regex: Custom slug regex pattern. If None, uses the
            DISPLAY_IDS["SLUG_REGEX"] setting (defaults to Django's pattern).

    Returns:
        A DisplayIDOrUUIDOrSlugConverter subclass with the custom regex.

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import (
            make_display_id_or_uuid_or_slug_converter,
        )

        # Lowercase slugs only
        Converter = make_display_id_or_uuid_or_slug_converter(r"[a-z0-9-]+")
        register_converter(Converter, "identifier")

        urlpatterns = [
            path("products/<identifier:id>/", ProductDetailView.as_view()),
        ]
    """
    pattern = slug_regex if slug_regex is not None else get_setting("SLUG_REGEX")

    class CustomDisplayIDOrUUIDOrSlugConverter(DisplayIDOrUUIDOrSlugConverter):
        regex = rf"(?:{DISPLAY_ID_REGEX}|{UUID_REGEX}|{pattern})"

    return CustomDisplayIDOrUUIDOrSlugConverter
