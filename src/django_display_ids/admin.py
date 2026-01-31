"""Django admin integration for display IDs."""

from __future__ import annotations

import contextlib
import uuid
from typing import TYPE_CHECKING, Any

from .encoding import decode_display_id

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.http import HttpRequest

__all__ = ["DisplayIDSearchMixin"]


class DisplayIDSearchMixin:
    """Mixin to enable searching by display_id or UUID in Django admin.

    Add this mixin to your ModelAdmin to allow searching by display ID
    (e.g., "inv_2aUyqjCzEIiEcYMKj7TZtw") or raw UUID
    (e.g., "550e8400-e29b-41d4-a716-446655440000") in the admin search box.

    The mixin decodes the identifier and searches by the UUID field.

    Example:
        from django.contrib import admin
        from django_display_ids.admin import DisplayIDSearchMixin

        @admin.register(Invoice)
        class InvoiceAdmin(DisplayIDSearchMixin, admin.ModelAdmin):
            list_display = ["id", "display_id", "name"]
            search_fields = ["name"]  # display_id/UUID search is automatic

    Attributes:
        uuid_field: Name of the UUID field to search. Defaults to model's
            uuid_field if using DisplayIDMixin, otherwise "id".
    """

    uuid_field: str | None = None
    model: type[Model]

    def _get_uuid_field(self) -> str:
        """Get the UUID field name to search."""
        if self.uuid_field is not None:
            return self.uuid_field
        # Try to get from model's uuid_field attribute
        uuid_field: str | None = getattr(self.model, "uuid_field", None)
        return uuid_field or "id"

    def _try_parse_uuid(self, value: str) -> uuid.UUID | None:
        """Try to parse a string as a UUID."""
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError):
            return None

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet[Any],
        search_term: str,
    ) -> tuple[QuerySet[Any], bool]:
        """Extend search to handle display IDs and raw UUIDs.

        Tries to match the search term as:
        1. A display ID (prefix_base62uuid) if it contains an underscore
        2. A raw UUID if it looks like a UUID format
        """
        queryset, use_distinct = super().get_search_results(  # type: ignore[misc]
            request, queryset, search_term
        )

        uuid_field = self._get_uuid_field()
        uuid_val = None

        # Try to decode as display_id if it contains an underscore
        if "_" in search_term:
            with contextlib.suppress(ValueError, TypeError):
                _prefix, uuid_val = decode_display_id(search_term)

        # Try to parse as raw UUID if not already matched
        if uuid_val is None:
            uuid_val = self._try_parse_uuid(search_term)

        # Add matching objects to queryset if we found a UUID
        if uuid_val is not None:
            queryset |= self.model._default_manager.filter(**{uuid_field: uuid_val})

        return queryset, use_distinct
