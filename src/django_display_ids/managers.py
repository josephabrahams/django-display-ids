"""Custom managers and querysets for display ID lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from django.db import models
from django.db.models import Q

from .conf import get_setting
from .encoding import decode_display_id
from .exceptions import (
    AmbiguousIdentifierError,
    InvalidIdentifierError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
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

    def get_by_display_id(
        self,
        value: str,
        *,
        prefix: str | None = None,
    ) -> M:
        """Get an object by its display ID.

        Args:
            value: The display ID string (e.g., "inv_1a2B3c4D5e6F7g8H").
            prefix: Expected prefix for validation. If None, uses model's prefix.

        Returns:
            The matching model instance.

        Raises:
            MissingPrefixError: If no prefix is configured on the model.
            InvalidIdentifierError: If the display ID format is invalid.
            UnknownPrefixError: If the prefix doesn't match expected.
            ObjectNotFoundError: If no matching object exists.
        """
        # Get model config
        model = self.model
        uuid_field = self._get_uuid_field()
        expected_prefix = prefix or self._get_model_prefix()

        # Require a prefix for display ID lookups
        if expected_prefix is None:
            raise MissingPrefixError(model_name=model.__name__)

        # Decode the display ID
        try:
            decoded_prefix, uuid_value = decode_display_id(value)
        except ValueError as e:
            raise InvalidIdentifierError(value, str(e)) from e

        # Validate prefix
        if decoded_prefix != expected_prefix:
            raise UnknownPrefixError(
                value, actual=decoded_prefix, expected=expected_prefix
            )

        # Query the database
        try:
            return self.get(**{uuid_field: uuid_value})
        except model.DoesNotExist:  # type: ignore[attr-defined]
            raise ObjectNotFoundError(value, model_name=model.__name__) from None

    def get_by_identifier(
        self,
        value: str,
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> M:
        """Get an object by any supported identifier type.

        Tries each strategy in order and returns the first match.

        Args:
            value: The identifier string (display ID, UUID, or slug).
            strategies: Strategies to try. Defaults to settings.
            prefix: Expected display ID prefix for validation.

        Returns:
            The matching model instance.

        Raises:
            InvalidIdentifierError: If no strategy can parse the identifier.
            UnknownPrefixError: If display ID prefix doesn't match expected.
            ObjectNotFoundError: If no matching object exists.
            AmbiguousIdentifierError: If multiple objects match (slug).
        """
        model = self.model
        uuid_field = self._get_uuid_field()
        slug_field = self._get_slug_field()
        expected_prefix = prefix or self._get_model_prefix()
        lookup_strategies = strategies or self._get_strategies()

        # Parse the identifier
        result = parse_identifier(
            value, lookup_strategies, expected_prefix=expected_prefix
        )

        # Build the lookup
        lookup: dict[str, Any]
        if result.strategy in ("uuid", "display_id"):
            lookup = {uuid_field: result.uuid}
        else:
            lookup = {slug_field: result.slug}

        # Execute the query
        try:
            return self.get(**lookup)
        except model.DoesNotExist:  # type: ignore[attr-defined]
            raise ObjectNotFoundError(value, model_name=model.__name__) from None
        except model.MultipleObjectsReturned:  # type: ignore[attr-defined]
            count = self.filter(**lookup).count()
            raise AmbiguousIdentifierError(value, count) from None

    def get_by_identifiers(
        self,
        values: Sequence[str],
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
    ) -> DisplayIDQuerySet[M]:
        """Get multiple objects by any supported identifier type in a single query.

        Parses each identifier to determine its type (display ID, UUID, or slug),
        then executes a single database query using `__in` lookups.

        Args:
            values: A sequence of identifier strings (display IDs, UUIDs, or slugs).
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
            ])
        """
        if not values:
            return self.none()

        uuid_field = self._get_uuid_field()
        slug_field = self._get_slug_field()
        expected_prefix = prefix or self._get_model_prefix()
        lookup_strategies = strategies or self._get_strategies()

        # Collect UUIDs and slugs separately
        uuids: list[Any] = []
        slugs: list[str] = []

        for value in values:
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

    def get_queryset(self) -> DisplayIDQuerySet[M]:
        return DisplayIDQuerySet(self.model, using=self._db)

    def get_by_display_id(
        self,
        value: str,
        *,
        prefix: str | None = None,
    ) -> M:
        """Get an object by its display ID.

        See DisplayIDQuerySet.get_by_display_id for details.
        """
        return self.get_queryset().get_by_display_id(value, prefix=prefix)

    def get_by_identifier(
        self,
        value: str,
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

    def get_by_identifiers(
        self,
        values: Sequence[str],
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
