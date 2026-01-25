"""Type definitions for django-display-ids."""

from __future__ import annotations

from typing import Literal

__all__ = [
    "DEFAULT_STRATEGIES",
    "StrategyName",
]

# Supported lookup strategy names
StrategyName = Literal["uuid", "display_id", "slug"]

# Default strategy order: display_id first (most specific), then uuid
# Slug is excluded by default since it's a catch-all that matches any string
DEFAULT_STRATEGIES: tuple[StrategyName, ...] = ("display_id", "uuid")
