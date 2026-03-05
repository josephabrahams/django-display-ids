"""Django admin integration for display IDs."""

from __future__ import annotations

import contextlib
import uuid
from typing import TYPE_CHECKING, Any

from .encoding import decode_display_id

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.http import HttpRequest

__all__ = ["DisplayIDAdminSearchMixin"]


class DisplayIDAdminSearchMixin:
    """Mixin to enable searching by display ID or raw UUID in Django admin.

    Add this mixin to your ModelAdmin to allow searching by display ID
    (e.g., "inv_2aUyqjCzEIiEcYMKj7TZtw") or raw UUID (with or without
    hyphens) in the admin search box.

    The mixin decodes the display ID or parses the UUID and does an exact
    match against the UUID field.

    Example:
        from django.contrib import admin
        from django_display_ids import DisplayIDAdminSearchMixin

        @admin.register(Invoice)
        class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            list_display = ["id", "display_id", "name"]
            search_fields = ["name"]  # display ID and UUID search is automatic

    Attributes:
        uuid_field: Name of the UUID field to search. Defaults to model's
            uuid_field if using DisplayIDModel, otherwise "id".
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

    @staticmethod
    def _parse_identifier(search_term: str) -> uuid.UUID | None:
        """Parse a search term as a display ID or raw UUID.

        Tries to decode as a display ID first (if it contains an underscore),
        then falls back to raw UUID parsing. Returns ``None`` if the search
        term is neither.

        Subclasses can use this to search additional UUID fields::

            def get_search_results(self, request, queryset, search_term):
                queryset, use_distinct = super().get_search_results(
                    request, queryset, search_term
                )
                if uuid_val := self._parse_identifier(search_term):
                    queryset |= self.model._default_manager.filter(
                        user__uid=uuid_val
                    )
                return queryset, use_distinct
        """
        uuid_val = None

        # Try to decode as display_id if it contains an underscore
        if "_" in search_term:
            with contextlib.suppress(ValueError, TypeError):
                _prefix, uuid_val = decode_display_id(search_term)

        # Try to parse as a raw UUID
        if uuid_val is None:
            with contextlib.suppress(ValueError):
                uuid_val = uuid.UUID(search_term)

        return uuid_val

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet[Any],
        search_term: str,
    ) -> tuple[QuerySet[Any], bool]:
        """Extend search to handle display IDs and raw UUIDs."""
        queryset, use_distinct = super().get_search_results(  # type: ignore[misc]
            request, queryset, search_term
        )

        uuid_val = self._parse_identifier(search_term)
        if uuid_val is not None:
            uuid_field = self._get_uuid_field()
            queryset |= self.model._default_manager.filter(**{uuid_field: uuid_val})

        return queryset, use_distinct
