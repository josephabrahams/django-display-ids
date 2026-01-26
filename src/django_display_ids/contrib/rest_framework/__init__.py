"""Django REST Framework integration for django-display-ids."""

import contextlib

from .serializers import DisplayIDField
from .views import DisplayIDLookupMixin

# Register drf-spectacular extension if available
# The extension auto-registers when the module is imported
with contextlib.suppress(ImportError):
    from django_display_ids.contrib import (
        drf_spectacular as _drf_spectacular,  # noqa: F401
    )

# OpenAPI parameter descriptions for consistent documentation
ID_PARAM_DESCRIPTION = "Identifier: display_id (prefix_xxx) or UUID"
ID_PARAM_DESCRIPTION_WITH_SLUG = "Identifier: display_id (prefix_xxx), UUID, or slug"


def id_param_description(prefix: str, *, with_slug: bool = False) -> str:
    """Generate ID parameter description with the actual prefix.

    Args:
        prefix: The display_id prefix (e.g., "user", "app").
        with_slug: Include slug as an identifier option.

    Returns:
        Description string for OpenAPI parameter.

    Example:
        >>> id_param_description("user")
        'Identifier: display_id (user_xxx) or UUID'

        >>> id_param_description("app", with_slug=True)
        'Identifier: display_id (app_xxx), UUID, or slug'
    """
    if with_slug:
        return f"Identifier: display_id ({prefix}_xxx), UUID, or slug"
    return f"Identifier: display_id ({prefix}_xxx) or UUID"


__all__ = [  # noqa: RUF022 - keep logical order for readability
    "DisplayIDField",
    "DisplayIDLookupMixin",
    "ID_PARAM_DESCRIPTION",
    "ID_PARAM_DESCRIPTION_WITH_SLUG",
    "id_param_description",
]
