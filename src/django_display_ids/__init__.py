"""django-display-ids: Resolve external identifiers to Django model instances.

This package provides a clean way to resolve external identifiers (UUIDs,
display IDs, slugs) to model instances in Django and DRF views without
requiring model inheritance, custom fields, or serializers.

Example:
    from django_display_ids import (
        encode_display_id,
        decode_display_id,
        resolve_object,
        DisplayIDMixin,
    )

    # Encode a UUID to a display ID
    display_id = encode_display_id("inv", invoice.id)
    # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

    # Use in Django views — prefix is inherited from the model
    class InvoiceDetailView(DisplayIDMixin, DetailView):
        model = Invoice
        lookup_param = "id"
"""

from importlib.metadata import version
from typing import Any

from .admin import DisplayIDAdminSearchMixin

__version__ = version("django-display-ids")
from .converters import (
    DisplayIDConverter,
    DisplayIDOrSlugConverter,
    DisplayIDOrUUIDConverter,
    DisplayIDOrUUIDOrSlugConverter,
    make_display_id_or_slug_converter,
    make_display_id_or_uuid_or_slug_converter,
)
from .encoding import (
    decode_display_id,
    decode_uuid,
    encode_display_id,
    encode_uuid,
)
from .examples import (
    example_display_id,
    example_uuid,
)
from .exceptions import (
    AmbiguousIdentifierError,
    DisplayIDLookupError,
    InvalidIdentifierError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
)
from .managers import DisplayIDManager, DisplayIDQuerySet
from .resolver import resolve_object
from .typing import DEFAULT_STRATEGIES, StrategyName
from .views import DisplayIDMixin


def __getattr__(name: str) -> Any:
    """Lazy import for model-related items to avoid app registry issues."""
    if name == "DisplayIDModel":
        from .models import DisplayIDModel

        return DisplayIDModel
    if name == "get_model_for_prefix":
        from .models import get_model_for_prefix

        return get_model_for_prefix
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [  # noqa: RUF022 - keep categorized order for readability
    # Model integration
    "DisplayIDModel",
    "DisplayIDManager",
    "DisplayIDQuerySet",
    "get_model_for_prefix",
    # View mixins
    "DisplayIDMixin",
    "DisplayIDAdminSearchMixin",
    # Encoding/decoding
    "encode_display_id",
    "decode_display_id",
    "encode_uuid",
    "decode_uuid",
    # URL converters
    "DisplayIDConverter",
    "DisplayIDOrUUIDConverter",
    "DisplayIDOrSlugConverter",
    "DisplayIDOrUUIDOrSlugConverter",
    "make_display_id_or_slug_converter",
    "make_display_id_or_uuid_or_slug_converter",
    # Core resolver
    "resolve_object",
    # Exceptions
    "DisplayIDLookupError",
    "InvalidIdentifierError",
    "UnknownPrefixError",
    "MissingPrefixError",
    "ObjectNotFoundError",
    "AmbiguousIdentifierError",
    # Examples (for OpenAPI)
    "example_display_id",
    "example_uuid",
    # Types
    "StrategyName",
    "DEFAULT_STRATEGIES",
    # Version
    "__version__",
]
