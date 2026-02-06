"""Configuration for django-display-ids.

Settings can be configured in Django settings under the DISPLAY_IDS namespace:

    DISPLAY_IDS = {
        "UUID_FIELD": "uid",
        "SLUG_FIELD": "slug",
        "STRATEGIES": ("display_id", "uuid", "slug"),
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.urls.converters import SlugConverter

if TYPE_CHECKING:
    from .typing import StrategyName

__all__ = [
    "DEFAULTS",
    "NOT_SET",
    "SLUG_REGEX",
    "get_setting",
    "get_slug_field",
    "get_uuid_field",
]

# Sentinel for distinguishing "not set" from None
NOT_SET: Any = object()

# Django's default slug regex pattern
SLUG_REGEX: str = SlugConverter.regex

DEFAULTS: dict[str, str | tuple[str, ...]] = {
    "UUID_FIELD": "id",
    "SLUG_FIELD": "slug",
    "STRATEGIES": ("display_id", "uuid", "slug"),
    "SLUG_REGEX": SLUG_REGEX,
}


def get_setting(name: str) -> str | tuple[StrategyName, ...]:
    """Get a setting value, with fallback to defaults.

    Args:
        name: The setting name (e.g., "UUID_FIELD", "STRATEGIES").

    Returns:
        The configured value or the default.

    Raises:
        KeyError: If the setting name is not recognized.
    """
    if name not in DEFAULTS:
        raise KeyError(f"Unknown setting: {name}")

    user_settings: dict[str, str | tuple[str, ...]] = getattr(
        settings, "DISPLAY_IDS", {}
    )
    result = user_settings.get(name, DEFAULTS[name])
    return result  # type: ignore[return-value]


def get_uuid_field(override: str | None) -> str:
    """Get the UUID field name, with optional override.

    Args:
        override: Explicit field name, or None to use settings default.

    Returns:
        The UUID field name.
    """
    if override is not None:
        return override
    return str(get_setting("UUID_FIELD"))


def get_slug_field(override: str | None) -> str:
    """Get the slug field name, with optional override.

    Args:
        override: Explicit field name, or None to use settings default.

    Returns:
        The slug field name.
    """
    if override is not None:
        return override
    return str(get_setting("SLUG_FIELD"))
