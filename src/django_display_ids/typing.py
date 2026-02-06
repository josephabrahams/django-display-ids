"""Type definitions for django-display-ids."""

from __future__ import annotations

from typing import Literal

__all__ = [
    "DEFAULT_STRATEGIES",
    "StrategyName",
]

# Supported lookup strategy names
StrategyName = Literal["uuid", "display_id", "slug"]

# Default strategy order: display_id first (most specific), then uuid, then slug
# Slug is a catch-all — it's safe to include by default because the manager
# and resolver automatically skip it for models without a slug field.
DEFAULT_STRATEGIES: tuple[StrategyName, ...] = ("display_id", "uuid", "slug")
