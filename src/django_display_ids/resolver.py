"""Core resolver for looking up model instances by identifier."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, TypeVar

from django.core.exceptions import FieldDoesNotExist
from django.db import models

from .conf import get_setting
from .encoding import PREFIX_PATTERN
from .exceptions import AmbiguousIdentifierError, ObjectNotFoundError
from .strategies import parse_identifier
from .typing import DEFAULT_STRATEGIES, StrategyName

if TYPE_CHECKING:
    from django.db.models import QuerySet

__all__ = [
    "resolve_object",
]

M = TypeVar("M", bound=models.Model)


def _resolve_uuid_field(model: type[models.Model], override: str | None) -> str:
    """Resolve the UUID field name for a model.

    Resolution order:
        1. Explicit *override* (if not None).
        2. ``model.uuid_field`` class attribute (set by ``DisplayIDModel``).
        3. ``DISPLAY_IDS["UUID_FIELD"]`` setting.
        4. ``"id"`` (the default for the setting).
    """
    if override is not None:
        return override
    model_field: str | None = getattr(model, "uuid_field", None)
    if model_field is not None:
        return model_field
    return str(get_setting("UUID_FIELD"))


def _resolve_slug_field(model: type[models.Model], override: str | None) -> str:
    """Resolve the slug field name for a model.

    Resolution order:
        1. Explicit *override* (if not None).
        2. ``model.slug_field`` class attribute (set by ``DisplayIDModel``).
        3. ``DISPLAY_IDS["SLUG_FIELD"]`` setting.
        4. ``"slug"`` (the default for the setting).
    """
    if override is not None:
        return override
    model_field: str | None = getattr(model, "slug_field", None)
    if model_field is not None:
        return model_field
    return str(get_setting("SLUG_FIELD"))


def _resolve_prefix(model: type[models.Model], override: str | None) -> str | None:
    """Resolve the display ID prefix for a model.

    Resolution order:
        1. Explicit *override* (if not None).
        2. ``model.display_id_prefix`` class attribute (set by ``DisplayIDModel``).

    Raises:
        ValueError: If the resolved prefix is not 1-16 lowercase letters.
    """
    if override is not None:
        prefix: str | None = override
    else:
        prefix = getattr(model, "display_id_prefix", None)
    if prefix is not None and not PREFIX_PATTERN.match(prefix):
        raise ValueError(
            f"display_id_prefix must be 1-16 lowercase letters, " f"got: {prefix!r}"
        )
    return prefix


def resolve_object(
    model: type[M],
    value: str | uuid.UUID,
    *,
    strategies: tuple[StrategyName, ...] = DEFAULT_STRATEGIES,
    prefix: str | None = None,
    uuid_field: str | None = None,
    slug_field: str | None = None,
    queryset: QuerySet[M] | None = None,
) -> M:
    """Resolve an identifier to a model instance.

    Tries each strategy in order and returns the first matching object.

    Args:
        model: The Django model class.
        value: The identifier string (UUID, display ID, or slug),
            or a UUID instance for direct UUID lookup.
        strategies: Tuple of strategy names to try in order.
        prefix: Expected display ID prefix. When ``None`` (the default),
            auto-detected from the model's ``display_id_prefix`` attribute.
        uuid_field: Name of the UUID field on the model. When ``None``
            (the default), auto-detected from the model's ``uuid_field``
            attribute, then the ``DISPLAY_IDS["UUID_FIELD"]`` setting,
            then ``"id"``.
        slug_field: Name of the slug field on the model. When ``None``
            (the default), auto-detected from the model's ``slug_field``
            attribute, then the ``DISPLAY_IDS["SLUG_FIELD"]`` setting,
            then ``"slug"``.
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
    # Resolve field names and prefix
    prefix = _resolve_prefix(model, prefix)
    uuid_field = _resolve_uuid_field(model, uuid_field)
    slug_field = _resolve_slug_field(model, slug_field)

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

    # UUID objects skip strategy parsing entirely
    if isinstance(value, uuid.UUID):
        try:
            return qs.get(**{uuid_field: value})
        except model.DoesNotExist:  # type: ignore[attr-defined]
            raise ObjectNotFoundError(str(value), model_name=model.__name__) from None

    # Skip slug strategy if the model has no slug field
    try:
        model._meta.get_field(slug_field)
    except FieldDoesNotExist:
        strategies = tuple(s for s in strategies if s != "slug")

    # Parse the identifier to determine type
    result = parse_identifier(value, strategies, expected_prefix=prefix)

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
