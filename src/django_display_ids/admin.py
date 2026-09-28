"""Django admin integration for display IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .exceptions import DisplayIDLookupError
from .resolver import _Lookup, _LookupOptions
from .strategies import parse_identifier

if TYPE_CHECKING:
    import uuid

    from django.db.models import Model, QuerySet
    from django.http import HttpRequest

__all__ = ["DisplayIDAdminSearchMixin"]


class DisplayIDAdminSearchMixin(_LookupOptions):
    """Mixin to enable searching by display ID, UUID, or slug in Django admin.

    The search term is parsed with the same strategies, prefix check, and
    field names as ``resolve_object()`` and the view mixins, and an exact
    match is added to the normal ``search_fields`` results.

    Example:
        from django.contrib import admin
        from django_display_ids import DisplayIDAdminSearchMixin

        @admin.register(Invoice)
        class InvoiceAdmin(DisplayIDAdminSearchMixin, admin.ModelAdmin):
            list_display = ["id", "display_id", "name"]
            search_fields = ["name"]  # display ID, UUID and slug are automatic

    Attributes:
        lookup_strategies: Strategies to try. Defaults to the
            ``DISPLAY_IDS["STRATEGIES"]`` setting.
        display_id_prefix: Expected display ID prefix. Defaults to the
            model's ``display_id_prefix``.
        uuid_field: UUID field name. Defaults to the model's ``uuid_field``,
            then the ``DISPLAY_IDS["UUID_FIELD"]`` setting, then ``"id"``.
        slug_field: Slug field name. Defaults to the model's ``slug_field``,
            then the ``DISPLAY_IDS["SLUG_FIELD"]`` setting, then ``"slug"``.
    """

    model: type[Model]

    @staticmethod
    def _parse_identifier(
        search_term: str, *, model: type[Model] | None = None
    ) -> uuid.UUID | None:
        """Parse a search term as a display ID or raw UUID.

        Leading and trailing whitespace is stripped, so identifiers pasted
        from a terminal or email still match. Returns ``None`` if the search
        term is neither.

        Args:
            search_term: The admin search box input.
            model: If given, the term is checked against that model's rules,
                the same way its own lookups are: a display ID must use its
                prefix, and on a model without a prefix only raw UUIDs match.
                Without it, a display ID with any prefix is accepted.

        Subclasses can use this to search additional UUID fields::

            def get_search_results(self, request, queryset, search_term):
                original_queryset = queryset
                queryset, use_distinct = super().get_search_results(
                    request, queryset, search_term
                )
                if uuid_val := self._parse_identifier(search_term, model=Customer):
                    queryset |= original_queryset.filter(customer_id=uuid_val)
                return queryset, use_distinct
        """
        try:
            if model is None:
                return parse_identifier(search_term, ("display_id", "uuid")).uuid
            lookup = _Lookup.for_model(model, strategies=("display_id", "uuid"))
            (uuid_val,) = lookup.build(search_term).values()
        except DisplayIDLookupError:
            return None
        return uuid_val  # type: ignore[no-any-return]

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet[Any],
        search_term: str,
    ) -> tuple[QuerySet[Any], bool]:
        """Add an exact display ID, UUID, or slug match to the search results."""
        original_queryset = queryset
        queryset, use_distinct = super().get_search_results(  # type: ignore[misc]
            request, queryset, search_term
        )

        # Outside the try: a misconfigured lookup is an error, not "no match"
        lookup = self._get_lookup(self.model)
        try:
            kwargs = lookup.build(search_term)
        except DisplayIDLookupError:
            return queryset, use_distinct

        queryset |= original_queryset.filter(**kwargs)
        return queryset, use_distinct
