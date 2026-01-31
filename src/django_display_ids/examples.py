"""Deterministic example generation for display IDs.

These functions generate consistent example UUIDs and display IDs based on
a prefix or model, useful for OpenAPI schema examples and documentation.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from .encoding import encode_uuid

if TYPE_CHECKING:
    from django.db.models import Model

__all__ = [
    "example_display_id",
    "example_uuid",
]


def _get_prefix(prefix_or_model: str | type[Model]) -> str:
    """Extract prefix from string or model class."""
    if isinstance(prefix_or_model, str):
        return prefix_or_model
    # It's a model class
    prefix: str | None = getattr(prefix_or_model, "display_id_prefix", None)
    if prefix is None:
        raise ValueError(f"Model {prefix_or_model.__name__} has no display_id_prefix")
    return prefix


def example_uuid(prefix_or_model: str | type[Model]) -> uuid.UUID:
    """Generate a deterministic UUID from a prefix or model.

    Uses SHA-256 hash of the prefix to generate a consistent UUID.
    This ensures the same prefix always produces the same example UUID.

    Args:
        prefix_or_model: Either a display ID prefix string (e.g., "app")
            or a model class with a display_id_prefix attribute.

    Returns:
        A deterministic UUID based on the prefix.

    Example:
        >>> example_uuid("app")
        UUID('a172cedc-ae47-474b-615c-54d510a5d84a')

        >>> example_uuid(App)  # Model with display_id_prefix = "app"
        UUID('a172cedc-ae47-474b-615c-54d510a5d84a')
    """
    prefix = _get_prefix(prefix_or_model)
    hash_bytes = hashlib.sha256(prefix.encode()).digest()[:16]
    return uuid.UUID(bytes=hash_bytes)


def example_display_id(prefix_or_model: str | type[Model]) -> str:
    """Generate a deterministic display ID example from a prefix or model.

    Combines the prefix with a base62-encoded UUID derived from
    the prefix itself.

    Args:
        prefix_or_model: Either a display ID prefix string (e.g., "app")
            or a model class with a display_id_prefix attribute.

    Returns:
        A complete display ID example (e.g., "app_4ueEO5Nz4X7u9qc3FVHokM").

    Example:
        >>> example_display_id("app")
        'app_4ueEO5Nz4X7u9qc3FVHokM'

        >>> example_display_id(App)  # Model with display_id_prefix = "app"
        'app_4ueEO5Nz4X7u9qc3FVHokM'
    """
    prefix = _get_prefix(prefix_or_model)
    ex_uuid = example_uuid(prefix)
    encoded = encode_uuid(ex_uuid)
    return f"{prefix}_{encoded}"


# Aliases for backwards compatibility
example_uuid_for_prefix = example_uuid
example_display_id_for_prefix = example_display_id
