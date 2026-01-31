"""Configuration for django-display-ids.

Settings can be configured in Django settings under the DISPLAY_IDS namespace:

    DISPLAY_IDS = {
        "UUID_FIELD": "uid",
        "SLUG_FIELD": "slug",
        "STRATEGIES": ("display_id", "uuid"),
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from .typing import StrategyName

__all__ = [
    "DEFAULTS",
    "get_setting",
]

DEFAULTS: dict[str, str | tuple[str, ...]] = {
    "UUID_FIELD": "id",
    "SLUG_FIELD": "slug",
    "STRATEGIES": ("display_id", "uuid"),
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
