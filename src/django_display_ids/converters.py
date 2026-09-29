"""Django URL path converters for display IDs and UUIDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .conf import SLUG_REGEX, get_setting
from .encoding import DISPLAY_ID_REGEX, UUID_REGEX

if TYPE_CHECKING:
    import uuid

__all__ = [
    "DISPLAY_ID_REGEX",
    "SLUG_REGEX",
    "UUID_REGEX",
    "DisplayIDConverter",
    "DisplayIDOrSlugConverter",
    "DisplayIDOrUUIDConverter",
    "DisplayIDOrUUIDOrSlugConverter",
    "make_display_id_or_slug_converter",
    "make_display_id_or_uuid_or_slug_converter",
]


class _SlugRegex:
    """Class attribute that builds ``regex`` as ``(?:alternatives|slug)``.

    Without a fixed *slug*, the ``SLUG_REGEX`` setting is read when Django
    compiles the URLconf rather than when this module is first imported, so
    ``override_settings`` works.
    """

    def __init__(self, *alternatives: str, slug: str | None = None) -> None:
        self.alternatives = alternatives
        self.slug = slug

    def __get__(self, obj: object, owner: type | None = None) -> str:
        slug = self.slug if self.slug is not None else str(get_setting("SLUG_REGEX"))
        return "(?:" + "|".join((*self.alternatives, slug)) + ")"


class BaseConverter:
    """Base class for the path converters.

    ``to_python`` passes the matched string through unchanged, since it may be
    a display ID, UUID, or slug. ``to_url`` calls ``str()`` like Django's
    ``<uuid:>`` converter, so ``reverse()`` accepts ``uuid.UUID`` objects.
    """

    def to_python(self, value: str) -> str:
        """Convert the URL value to a Python object."""
        return value

    def to_url(self, value: str | uuid.UUID) -> str:
        """Convert a Python object to a URL string."""
        return str(value)


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
    - UUID: hyphenated, in either case

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

    regex: str = _SlugRegex(DISPLAY_ID_REGEX)  # type: ignore[assignment]


class DisplayIDOrUUIDOrSlugConverter(BaseConverter):
    """Path converter for display IDs, UUIDs, or slugs.

    Matches any of:
    - Display ID: {prefix}_{base62}
    - UUID: hyphenated, in either case
    - Slug: matches DISPLAY_IDS["SLUG_REGEX"] setting (default: [-a-zA-Z0-9_]+)

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import DisplayIDOrUUIDOrSlugConverter

        register_converter(DisplayIDOrUUIDOrSlugConverter, "identifier")

        urlpatterns = [
            path("products/<identifier:id>/", ProductDetailView.as_view()),
        ]
    """

    regex: str = _SlugRegex(DISPLAY_ID_REGEX, UUID_REGEX)  # type: ignore[assignment]


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

    class CustomDisplayIDOrSlugConverter(DisplayIDOrSlugConverter):
        regex: str = _SlugRegex(DISPLAY_ID_REGEX, slug=slug_regex)  # type: ignore[assignment]

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

    class CustomDisplayIDOrUUIDOrSlugConverter(DisplayIDOrUUIDOrSlugConverter):
        regex: str = _SlugRegex(DISPLAY_ID_REGEX, UUID_REGEX, slug=slug_regex)  # type: ignore[assignment]

    return CustomDisplayIDOrUUIDOrSlugConverter
