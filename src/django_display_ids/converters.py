"""Django URL path converters for display IDs and UUIDs."""

from __future__ import annotations

__all__ = [
    "DisplayIDConverter",
    "DisplayIDOrUUIDConverter",
    "UUIDConverter",
]


class DisplayIDConverter:
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

    regex = r"[a-z]{1,16}_[0-9A-Za-z]{22}"

    def to_python(self, value: str) -> str:
        """Convert the URL value to a Python object."""
        return value

    def to_url(self, value: str) -> str:
        """Convert a Python object to a URL string."""
        return value


class UUIDConverter:
    """Path converter for UUIDs.

    Matches UUIDs in both hyphenated and unhyphenated formats:
    - 550e8400-e29b-41d4-a716-446655440000 (hyphenated)
    - 550e8400e29b41d4a716446655440000 (unhyphenated)

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import UUIDConverter

        register_converter(UUIDConverter, "uuid")

        urlpatterns = [
            path("invoices/<uuid:id>/", InvoiceDetailView.as_view()),
        ]

    Note:
        Django's built-in UUIDConverter only accepts hyphenated UUIDs.
        This converter is more permissive.
    """

    # Hyphenated: 8-4-4-4-12 hex chars with hyphens
    # Unhyphenated: 32 hex chars
    # Note: Parentheses group the alternatives so ^ and $ anchor correctly
    regex = (
        r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32})"
    )

    def to_python(self, value: str) -> str:
        """Convert the URL value to a Python object."""
        return value

    def to_url(self, value: str) -> str:
        """Convert a Python object to a URL string."""
        return value


class DisplayIDOrUUIDConverter:
    """Path converter for display IDs or UUIDs.

    Matches either format:
    - Display ID: {prefix}_{base62}
    - UUID: hyphenated or unhyphenated

    Example:
        from django.urls import path, register_converter
        from django_display_ids.converters import DisplayIDOrUUIDConverter

        register_converter(DisplayIDOrUUIDConverter, "display_id_or_uuid")

        urlpatterns = [
            path("invoices/<display_id_or_uuid:id>/", InvoiceDetailView.as_view()),
        ]
    """

    # Note: Parentheses group the alternatives so ^ and $ anchor correctly
    regex = (
        r"(?:"
        r"[a-z]{1,16}_[0-9A-Za-z]{22}"
        r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        r"|[0-9a-f]{32}"
        r")"
    )

    def to_python(self, value: str) -> str:
        """Convert the URL value to a Python object."""
        return value

    def to_url(self, value: str) -> str:
        """Convert a Python object to a URL string."""
        return value
