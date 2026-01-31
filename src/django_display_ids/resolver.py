"""Core resolver for looking up model instances by identifier."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from django.db import models

from .exceptions import AmbiguousIdentifierError, ObjectNotFoundError
from .strategies import parse_identifier
from .typing import DEFAULT_STRATEGIES, StrategyName

if TYPE_CHECKING:
    from django.db.models import QuerySet

__all__ = [
    "resolve_object",
]

M = TypeVar("M", bound=models.Model)


def resolve_object(
    *,
    model: type[M],
    value: str,
    strategies: tuple[StrategyName, ...] = DEFAULT_STRATEGIES,
    prefix: str | None = None,
    uuid_field: str = "id",
    slug_field: str = "slug",
    queryset: QuerySet[M] | None = None,
) -> M:
    """Resolve an identifier to a model instance.

    Tries each strategy in order and returns the first matching object.

    Args:
        model: The Django model class.
        value: The identifier string (UUID, display ID, or slug).
        strategies: Tuple of strategy names to try in order.
        prefix: Expected display ID prefix (for validation).
        uuid_field: Name of the UUID field on the model.
        slug_field: Name of the slug field on the model.
        queryset: Optional pre-filtered queryset to search within.

    Returns:
        The matching model instance.

    Raises:
        InvalidIdentifierError: If the identifier format is invalid.
        UnknownPrefixError: If display ID prefix doesn't match expected.
        ObjectNotFoundError: If no matching object exists.
        AmbiguousIdentifierError: If multiple objects match (slug lookup).
        TypeError: If queryset is not for the specified model.
    """
    # Parse the identifier to determine type
    result = parse_identifier(value, strategies, expected_prefix=prefix)

    # Get the base queryset
    if queryset is not None:
        if queryset.model is not model:
            raise TypeError(
                f"queryset must be for {model.__name__}, "
                f"got queryset for {queryset.model.__name__}"
            )
        qs: QuerySet[M] = queryset
    else:
        qs = model._default_manager.all()

    # Build the lookup based on strategy
    lookup: dict[str, Any]
    if result.strategy in ("uuid", "display_id"):
        # Both UUID and display_id resolve to a UUID lookup
        lookup = {uuid_field: result.uuid}
    else:
        # Slug lookup
        lookup = {slug_field: result.slug}

    # Execute the query
    try:
        return qs.get(**lookup)
    except model.DoesNotExist:  # type: ignore[attr-defined]
        raise ObjectNotFoundError(value, model_name=model.__name__) from None
    except model.MultipleObjectsReturned:  # type: ignore[attr-defined]
        count = qs.filter(**lookup).count()
        raise AmbiguousIdentifierError(value, count) from None
