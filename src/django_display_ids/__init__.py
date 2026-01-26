"""django-display-ids: Resolve external identifiers to Django model instances.

This package provides a clean way to resolve external identifiers (UUIDs,
display IDs, slugs) to model instances in Django and DRF views without
requiring model inheritance, custom fields, or serializers.

Example:
    from django_display_ids import (
        encode_display_id,
        decode_display_id,
        resolve_object,
        DisplayIDObjectMixin,
    )

    # Encode a UUID to a display ID
    display_id = encode_display_id("inv", invoice.id)
    # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

    # Use in Django views
    class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
        model = Invoice
        lookup_param = "id"
        display_id_prefix = "inv"
"""

from .admin import DisplayIDSearchMixin
from .encoding import (
    decode_display_id,
    decode_uuid,
    encode_display_id,
    encode_uuid,
)
from .examples import (
    example_display_id,
    example_display_id_for_prefix,
    example_uuid,
    example_uuid_for_prefix,
)
from .exceptions import (
    AmbiguousIdentifierError,
    InvalidIdentifierError,
    LookupError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
)
from .managers import DisplayIDManager, DisplayIDQuerySet
from .models import DisplayIDMixin, get_model_for_prefix
from .resolver import resolve_object
from .typing import DEFAULT_STRATEGIES, StrategyName
from .views import DisplayIDObjectMixin

__all__ = [  # noqa: RUF022 - keep categorized order for readability
    # Encoding
    "encode_uuid",
    "decode_uuid",
    "encode_display_id",
    "decode_display_id",
    # Examples (for OpenAPI schemas, documentation)
    "example_uuid",
    "example_display_id",
    "example_uuid_for_prefix",  # alias
    "example_display_id_for_prefix",  # alias
    # Core resolver
    "resolve_object",
    # Errors
    "LookupError",
    "InvalidIdentifierError",
    "UnknownPrefixError",
    "MissingPrefixError",
    "ObjectNotFoundError",
    "AmbiguousIdentifierError",
    # Django mixins
    "DisplayIDObjectMixin",
    # Admin mixins
    "DisplayIDSearchMixin",
    # Model mixin
    "DisplayIDMixin",
    "get_model_for_prefix",
    # Managers
    "DisplayIDManager",
    "DisplayIDQuerySet",
    # Types
    "StrategyName",
    "DEFAULT_STRATEGIES",
]

__version__ = "0.1.1"


def get_drf_mixin():
    """Lazily import the DRF mixin to avoid hard dependency.

    Returns:
        DisplayIDLookupMixin class.

    Raises:
        ImportError: If Django REST Framework is not installed.
    """
    from .contrib.rest_framework import DisplayIDLookupMixin

    return DisplayIDLookupMixin
