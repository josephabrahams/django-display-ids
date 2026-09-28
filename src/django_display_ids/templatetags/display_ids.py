"""Template tags and filters for generating display IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import template

from ..encoding import encode_display_id

if TYPE_CHECKING:
    import uuid

__all__ = [
    "display_id",
]

register = template.Library()


@register.filter(name="display_id")
def display_id(value: uuid.UUID | str | None, prefix: str) -> str:
    """Encode a UUID as a display ID.

    Usage:
        {{ some_uuid|display_id:"inv" }}
        {{ invoice.customer_id|display_id:"cust" }}

    Args:
        value: UUID to encode, as a UUID object or a UUID string.
        prefix: Display ID prefix (1-16 lowercase letters).

    Returns:
        Display ID string like "inv_2aUyqjCzEIiEcYMKj7TZtw", or empty string
        if value is None.

    Raises:
        TemplateSyntaxError: If prefix is invalid or value is not a UUID.
    """
    if value is None:
        return ""

    try:
        return encode_display_id(prefix, value)
    except (ValueError, TypeError) as e:
        raise template.TemplateSyntaxError(f"display_id filter: {e}") from e
