"""Django admin integration for display IDs."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, ClassVar

from django.db.models import Q

from . import checks
from .exceptions import DisplayIDLookupError
from .resolver import _Lookup, _LookupOptions
from .strategies import parse_identifier

if TYPE_CHECKING:
    import uuid
    from collections.abc import Mapping

    from django.core.checks import CheckMessage
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
        display_id_search_fields: Other UUID fields to search, mapped to the
            model whose display IDs they hold. Each gets an exact match,
            parsed like ``parse_search_uuid(term, model=...)``. ``None``
            accepts a display ID with any prefix::

                display_id_search_fields = {
                    "customer_id": Customer,
                    "request_uid": None,
                }
    """

    model: type[Model]
    display_id_search_fields: ClassVar[Mapping[str, type[Model] | None]] = {}

    def check(self, **kwargs: Any) -> list[CheckMessage]:
        """Add this library's checks to the admin's (see ``checks.py``)."""
        return [*super().check(**kwargs), *checks.check_admin(self)]  # type: ignore[misc]

    @staticmethod
    def parse_search_uuid(
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

        For a plain exact match on another UUID field, use
        ``display_id_search_fields`` instead. For anything else, call this
        from ``get_search_results()``::

            def get_search_results(self, request, queryset, search_term):
                original_queryset = queryset
                queryset, use_distinct = super().get_search_results(
                    request, queryset, search_term
                )
                if uuid_val := self.parse_search_uuid(search_term, model=Customer):
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

    @staticmethod
    def _parse_identifier(
        search_term: str, *, model: type[Model] | None = None
    ) -> uuid.UUID | None:
        """Deprecated alias for ``parse_search_uuid()``."""
        warnings.warn(
            "_parse_identifier() is deprecated, use parse_search_uuid() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DisplayIDAdminSearchMixin.parse_search_uuid(search_term, model=model)

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet[Any],
        search_term: str,
    ) -> tuple[QuerySet[Any], bool]:
        """Add exact display ID, UUID, or slug matches to the search results.

        Matches the model's own identifier, plus each field in
        ``display_id_search_fields``.
        """
        # Imported here so importing this package doesn't load the admin
        from django.contrib.admin.utils import lookup_spawns_duplicates

        original_queryset = queryset
        queryset, use_distinct = super().get_search_results(  # type: ignore[misc]
            request, queryset, search_term
        )

        # Outside the try: a misconfigured lookup is an error, not "no match"
        lookup = self._get_lookup(self.model)
        try:
            query = Q(**lookup.build(search_term))
        except DisplayIDLookupError:
            query = Q()

        for field, model in self.display_id_search_fields.items():
            uuid_val = self.parse_search_uuid(search_term, model=model)
            if uuid_val is not None:
                query |= Q(**{field: uuid_val})
                use_distinct = use_distinct or lookup_spawns_duplicates(
                    self.model._meta, field
                )

        if query:
            queryset |= original_queryset.filter(query)
        return queryset, use_distinct
