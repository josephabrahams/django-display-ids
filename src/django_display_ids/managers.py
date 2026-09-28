"""Custom managers and querysets for display ID lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, TypeVar

from django.db import models
from django.db.models import Q

from .exceptions import (
    DisplayIDLookupError,
)
from .resolver import _Lookup

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from .typing import StrategyName

__all__ = [
    "DisplayIDManager",
    "DisplayIDQuerySet",
]

M = TypeVar("M", bound=models.Model)


class DisplayIDQuerySet(models.QuerySet[M]):
    """QuerySet with display ID lookup methods.

    Example:
        class Invoice(DisplayIDModel):
            display_id_prefix = "inv"
            objects = DisplayIDManager()

        # Get by any identifier type
        invoice = Invoice.objects.get_by_identifier("inv_2aUyqjCzEIiEcYMKj7TZtw")

        # Works with filtered querysets
        invoice = Invoice.objects.filter(active=True).get_by_identifier("inv_xxx")

        # Get by display ID only (stricter)
        invoice = Invoice.objects.get_by_display_id("inv_2aUyqjCzEIiEcYMKj7TZtw")
    """

    # Re-annotate inherited QuerySet methods with -> Self so that
    # display ID methods remain visible to type checkers after chaining
    # (e.g. Invoice.objects.filter(...).get_by_identifier(...)).
    def filter(self, *args: Any, **kwargs: Any) -> Self:
        return super().filter(*args, **kwargs)

    def exclude(self, *args: Any, **kwargs: Any) -> Self:
        return super().exclude(*args, **kwargs)

    def select_related(self, *fields: Any) -> Self:
        return super().select_related(*fields)

    def prefetch_related(self, *lookups: Any) -> Self:
        return super().prefetch_related(*lookups)

    def order_by(self, *fields: Any) -> Self:
        return super().order_by(*fields)

    def distinct(self, *fields: Any) -> Self:
        return super().distinct(*fields)

    def all(self) -> Self:
        return super().all()

    def none(self) -> Self:
        return super().none()

    def get_by_display_id(
        self,
        value: str | uuid.UUID,
        *,
        prefix: str | None = None,
    ) -> M:
        """Get an object by its display ID.

        Args:
            value: The display ID string (e.g., "inv_2aUyqjCzEIiEcYMKj7TZtw"),
                or a UUID instance for direct UUID lookup.
            prefix: Expected prefix for validation. If None, uses model's prefix.

        Returns:
            The matching model instance.

        Raises:
            Model.DoesNotExist: If no matching object exists, if the display ID
                format is invalid, or if the prefix doesn't match.
            MissingPrefixError: If no prefix is configured on the model.
        """
        lookup = _Lookup.for_model(
            self.model, strategies=("display_id",), prefix=prefix
        )
        return self.get(**self._build(lookup, value))

    def get_by_identifier(
        self,
        value: str | uuid.UUID,
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> M:
        """Get an object by any supported identifier type.

        Tries each strategy in order and returns the first match.

        Args:
            value: The identifier string (display ID, UUID, or slug),
                or a UUID instance for direct UUID lookup.
            strategies: Strategies to try. Defaults to settings.
            prefix: Expected display ID prefix for validation.

        Returns:
            The matching model instance.

        Raises:
            Model.DoesNotExist: If the identifier cannot be parsed or
                no matching object exists.
            Model.MultipleObjectsReturned: If multiple objects match (slug).
        """
        lookup = _Lookup.for_model(self.model, strategies=strategies, prefix=prefix)
        return self.get(**self._build(lookup, value))

    def resolve_identifier(
        self,
        value: str | uuid.UUID,
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> uuid.UUID:
        """Resolve an identifier to a UUID without fetching the object.

        For UUID and display_id identifiers, the UUID is extracted by parsing
        alone, with no database query. Only slug identifiers require a
        database lookup.

        This is useful for cursor-based pagination where you need the UUID
        value to build a WHERE clause but don't need the full model instance.

        Args:
            value: The identifier string (display ID, UUID, or slug),
                or a UUID instance (returned as-is).
            strategies: Strategies to try. Defaults to settings.
            prefix: Expected display ID prefix for validation.

        Returns:
            The resolved UUID value.

        Raises:
            Model.DoesNotExist: If the identifier cannot be parsed or
                no matching object exists (slug lookup).
            Model.MultipleObjectsReturned: If multiple objects match (slug).
        """
        lookup = _Lookup.for_model(self.model, strategies=strategies, prefix=prefix)
        kwargs = self._build(lookup, value)

        # UUID and display ID lookups already hold the UUID, so no query
        if lookup.uuid_field in kwargs:
            return kwargs[lookup.uuid_field]  # type: ignore[no-any-return]

        # Slug lookups need a query
        return getattr(self.get(**kwargs), lookup.uuid_field)  # type: ignore[no-any-return]

    def get_by_identifiers(
        self,
        values: Sequence[str | uuid.UUID],
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> DisplayIDQuerySet[M]:
        """Get multiple objects by any supported identifier type in a single query.

        Parses each identifier to determine its type (display ID, UUID, or slug),
        then executes a single database query using `__in` lookups.

        Args:
            values: A sequence of identifier strings (display IDs, UUIDs, or slugs)
                or UUID instances. UUID instances skip strategy parsing.
            strategies: Strategies to try. Defaults to settings.
            prefix: Expected display ID prefix for validation.

        Returns:
            A queryset containing matching objects. Order is not guaranteed
            to match input order. Identifiers that match nothing are left
            out, whether no row exists or the identifier is invalid or has
            the wrong prefix, the same inputs ``get_by_identifier()``
            rejects with ``DoesNotExist``.

        Example:
            invoices = Invoice.objects.get_by_identifiers([
                'inv_2aUyqjCzEIiEcYMKj7TZtw',
                'inv_7kN3xPqRmLwYvTzJ5HfUaB',
                '550e8400-e29b-41d4-a716-446655440000',
                uuid.UUID('550e8400-e29b-41d4-a716-446655440000'),
            ])
        """
        if not values:
            return self.none()

        lookup = _Lookup.for_model(self.model, strategies=strategies, prefix=prefix)

        # Group values by field so the query is one IN per field
        by_field: dict[str, list[Any]] = {}
        for value in values:
            try:
                kwargs = lookup.build(value)
            except DisplayIDLookupError:
                continue  # can't match anything, like a missing row
            for field, field_value in kwargs.items():
                by_field.setdefault(field, []).append(field_value)

        # An empty Q() would match every row
        if not by_field:
            return self.none()

        query = Q()
        for field, field_values in by_field.items():
            query |= Q(**{f"{field}__in": field_values})
        return self.filter(query)

    def _build(self, lookup: _Lookup, value: str | uuid.UUID) -> dict[str, Any]:
        """Build a lookup, raising ``Model.DoesNotExist`` on bad input like ``get()``."""
        try:
            return lookup.build(value)
        except DisplayIDLookupError as e:
            raise self.model.DoesNotExist(  # type: ignore[attr-defined]
                f"{self.model.__name__}: {e}"
            ) from e


class DisplayIDManager(models.Manager[M]):
    """Manager that uses DisplayIDQuerySet.

    Example:
        class Invoice(DisplayIDModel):
            display_id_prefix = "inv"
            objects = DisplayIDManager()
    """

    _queryset_class = DisplayIDQuerySet

    if TYPE_CHECKING:

        def get_queryset(self) -> DisplayIDQuerySet[M]: ...

    def get_by_display_id(
        self,
        value: str | uuid.UUID,
        *,
        prefix: str | None = None,
    ) -> M:
        """Get an object by its display ID.

        See DisplayIDQuerySet.get_by_display_id for details.
        """
        return self.get_queryset().get_by_display_id(value, prefix=prefix)

    def get_by_identifier(
        self,
        value: str | uuid.UUID,
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> M:
        """Get an object by any supported identifier type.

        See DisplayIDQuerySet.get_by_identifier for details.
        """
        return self.get_queryset().get_by_identifier(
            value, strategies=strategies, prefix=prefix
        )

    def resolve_identifier(
        self,
        value: str | uuid.UUID,
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> uuid.UUID:
        """Resolve an identifier to a UUID without fetching the object.

        See DisplayIDQuerySet.resolve_identifier for details.
        """
        return self.get_queryset().resolve_identifier(
            value, strategies=strategies, prefix=prefix
        )

    def get_by_identifiers(
        self,
        values: Sequence[str | uuid.UUID],
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> DisplayIDQuerySet[M]:
        """Get multiple objects by any supported identifier type.

        See DisplayIDQuerySet.get_by_identifiers for details.
        """
        return self.get_queryset().get_by_identifiers(
            values, strategies=strategies, prefix=prefix
        )
