"""Django admin integration for display IDs."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from .encoding import decode_display_id

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.http import HttpRequest

__all__ = ["DisplayIDAdminSearchMixin"]


class DisplayIDAdminSearchMixin:
    """Mixin to enable searching by display ID in Django admin.

    Add this mixin to your ModelAdmin to allow searching by display ID
    (e.g., "inv_2aUyqjCzEIiEcYMKj7TZtw") in the admin search box.

    The mixin decodes the display ID and searches by the UUID field.

    For raw UUID search, add the UUID field to ``search_fields`` instead::

        search_fields = ["name", "id"]  # "id" enables raw UUID search

    Example:
        from django.contrib import admin
        from django_display_ids import DisplayIDAdminSearchMixin

        @admin.register(Invoice)
        class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            list_display = ["id", "display_id", "name"]
            search_fields = ["name"]  # display ID search is automatic

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

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet[Any],
        search_term: str,
    ) -> tuple[QuerySet[Any], bool]:
        """Extend search to handle display IDs.

        Tries to decode the search term as a display ID (prefix_base62uuid)
        if it contains an underscore.
        """
        queryset, use_distinct = super().get_search_results(  # type: ignore[misc]
            request, queryset, search_term
        )

        # Try to decode as display_id if it contains an underscore
        if "_" in search_term:
            uuid_field = self._get_uuid_field()
            with contextlib.suppress(ValueError, TypeError):
                _prefix, uuid_val = decode_display_id(search_term)
                queryset |= self.model._default_manager.filter(**{uuid_field: uuid_val})

        return queryset, use_distinct
