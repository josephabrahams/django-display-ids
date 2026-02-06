"""Custom managers and querysets for display ID lookups."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Self, TypeVar

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Q

from .conf import get_setting
from .encoding import decode_display_id
from .exceptions import (
    DisplayIDLookupError,
    MissingPrefixError,
)
from .strategies import parse_identifier

if TYPE_CHECKING:
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
        class Invoice(DisplayIDMixin, models.Model):
            display_id_prefix = "inv"
            objects = DisplayIDManager()

        # Get by any identifier type
        invoice = Invoice.objects.get_by_identifier("inv_1a2B3c4D5e6F7g8H")

        # Works with filtered querysets
        invoice = Invoice.objects.filter(active=True).get_by_identifier("inv_xxx")

        # Get by display ID only (stricter)
        invoice = Invoice.objects.get_by_display_id("inv_1a2B3c4D5e6F7g8H")
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
            value: The display ID string (e.g., "inv_1a2B3c4D5e6F7g8H"),
                or a UUID instance for direct UUID lookup.
            prefix: Expected prefix for validation. If None, uses model's prefix.

        Returns:
            The matching model instance.

        Raises:
            Model.DoesNotExist: If no matching object exists, if the display ID
                format is invalid, or if the prefix doesn't match.
            MissingPrefixError: If no prefix is configured on the model.
        """
        model = self.model
        uuid_field = self._get_uuid_field()

        # UUID objects skip display ID parsing entirely
        if isinstance(value, uuid.UUID):
            return self.get(**{uuid_field: value})

        # Get model config
        expected_prefix = prefix or self._get_model_prefix()

        # Require a prefix for display ID lookups
        if expected_prefix is None:
            raise MissingPrefixError(model_name=model.__name__)

        # Decode the display ID and validate prefix
        try:
            decoded_prefix, uuid_value = decode_display_id(value)
        except ValueError as e:
            raise model.DoesNotExist(  # type: ignore[attr-defined]
                f"{model.__name__}: invalid display ID: {value!r}"
            ) from e

        if decoded_prefix != expected_prefix:
            raise model.DoesNotExist(  # type: ignore[attr-defined]
                f"{model.__name__}: unknown prefix {decoded_prefix!r} "
                f"in {value!r}, expected {expected_prefix!r}"
            )

        # Query the database
        return self.get(**{uuid_field: uuid_value})

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
        model = self.model
        uuid_field = self._get_uuid_field()

        # UUID objects skip strategy parsing entirely
        if isinstance(value, uuid.UUID):
            return self.get(**{uuid_field: value})

        slug_field = self._get_slug_field()
        expected_prefix = prefix or self._get_model_prefix()
        lookup_strategies = strategies or self._get_strategies()

        # Skip slug strategy if the model has no slug field
        if not self._has_slug_field(slug_field):
            lookup_strategies = tuple(s for s in lookup_strategies if s != "slug")

        # Parse the identifier
        try:
            result = parse_identifier(
                value, lookup_strategies, expected_prefix=expected_prefix
            )
        except DisplayIDLookupError as e:
            raise model.DoesNotExist(  # type: ignore[attr-defined]
                f"{model.__name__}: {e}"
            ) from e

        # Build the lookup
        lookup: dict[str, Any]
        if result.strategy in ("uuid", "display_id"):
            lookup = {uuid_field: result.uuid}
        else:
            lookup = {slug_field: result.slug}

        # Execute the query
        return self.get(**lookup)

    def resolve_identifier(
        self,
        value: str | uuid.UUID,
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> uuid.UUID:
        """Resolve an identifier to a UUID without fetching the object.

        For UUID and display_id identifiers, the UUID is extracted by parsing
        alone — no database query is needed. Only slug identifiers require a
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
        model = self.model
        uuid_field = self._get_uuid_field()

        # UUID objects are returned as-is
        if isinstance(value, uuid.UUID):
            return value

        slug_field = self._get_slug_field()
        expected_prefix = prefix or self._get_model_prefix()
        lookup_strategies = strategies or self._get_strategies()

        # Skip slug strategy if the model has no slug field
        if not self._has_slug_field(slug_field):
            lookup_strategies = tuple(s for s in lookup_strategies if s != "slug")

        # Parse the identifier
        try:
            result = parse_identifier(
                value, lookup_strategies, expected_prefix=expected_prefix
            )
        except DisplayIDLookupError as e:
            raise model.DoesNotExist(  # type: ignore[attr-defined]
                f"{model.__name__}: {e}"
            ) from e

        # UUID and display_id strategies yield a UUID directly — no DB query
        if result.strategy in ("uuid", "display_id"):
            return result.uuid  # type: ignore[return-value]

        # Slug strategy requires a DB lookup
        obj = self.get(**{slug_field: result.slug})
        return getattr(obj, uuid_field)  # type: ignore[no-any-return]

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
            to match input order. Missing identifiers are silently excluded.

        Raises:
            InvalidIdentifierError: If any identifier cannot be parsed.

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

        uuid_field = self._get_uuid_field()
        slug_field = self._get_slug_field()
        expected_prefix = prefix or self._get_model_prefix()
        lookup_strategies = strategies or self._get_strategies()

        # Skip slug strategy if the model has no slug field
        if not self._has_slug_field(slug_field):
            lookup_strategies = tuple(s for s in lookup_strategies if s != "slug")

        # Collect UUIDs and slugs separately
        uuids: list[Any] = []
        slugs: list[str] = []

        for value in values:
            # UUID objects skip strategy parsing entirely
            if isinstance(value, uuid.UUID):
                uuids.append(value)
                continue

            result = parse_identifier(
                value, lookup_strategies, expected_prefix=expected_prefix
            )
            if result.strategy in ("uuid", "display_id"):
                uuids.append(result.uuid)
            else:
                slugs.append(result.slug)  # type: ignore[arg-type]

        # Build query with OR conditions
        query = Q()
        if uuids:
            query |= Q(**{f"{uuid_field}__in": uuids})
        if slugs:
            query |= Q(**{f"{slug_field}__in": slugs})

        return self.filter(query)

    def _get_uuid_field(self) -> str:
        """Get the UUID field name for this model."""
        if hasattr(self.model, "_get_uuid_field"):
            result: str = self.model._get_uuid_field()  # type: ignore[attr-defined]
            return result
        return str(get_setting("UUID_FIELD"))

    def _get_slug_field(self) -> str:
        """Get the slug field name for this model."""
        if hasattr(self.model, "_get_slug_field"):
            result: str = self.model._get_slug_field()  # type: ignore[attr-defined]
            return result
        return str(get_setting("SLUG_FIELD"))

    def _get_strategies(self) -> tuple[StrategyName, ...]:
        """Get the default strategies."""
        return get_setting("STRATEGIES")  # type: ignore[return-value]

    def _has_slug_field(self, slug_field: str) -> bool:
        """Check whether the model has the configured slug field."""
        try:
            self.model._meta.get_field(slug_field)
            return True
        except FieldDoesNotExist:
            return False

    def _get_model_prefix(self) -> str | None:
        """Get the display ID prefix from the model, if defined."""
        if hasattr(self.model, "get_display_id_prefix"):
            try:
                result: str | None = self.model.get_display_id_prefix()  # type: ignore[attr-defined]
                return result
            except NotImplementedError:
                return None
        return None


class DisplayIDManager(models.Manager[M]):
    """Manager that uses DisplayIDQuerySet.

    Example:
        class Invoice(DisplayIDMixin, models.Model):
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
