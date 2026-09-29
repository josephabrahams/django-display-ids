"""Core resolver for looking up model instances by identifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from django.db.models import Q

from .conf import get_setting
from .encoding import PREFIX_PATTERN, encode_display_id
from .exceptions import (
    AmbiguousIdentifierError,
    DisplayIDLookupError,
    MissingPrefixError,
    ObjectNotFoundError,
)
from .strategies import parse_identifier
from .typing import StrategyName  # noqa: TC001

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

    from django.db.models import QuerySet

__all__ = [
    "resolve_object",
    "resolve_objects",
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
            f"display_id_prefix must be 1-16 lowercase letters, got: {prefix!r}"
        )
    return prefix


@dataclass(frozen=True)
class _Lookup:
    """Lookup settings for one model, resolved once.

    Every lookup path builds its query through here, so they all accept and
    reject the same identifiers.
    """

    model_name: str
    prefix: str | None
    uuid_field: str
    slug_field: str
    strategies: tuple[StrategyName, ...]

    @classmethod
    def for_model(
        cls,
        model: type[models.Model],
        *,
        strategies: tuple[StrategyName, ...] | None = None,
        prefix: str | None = None,
        uuid_field: str | None = None,
        slug_field: str | None = None,
    ) -> _Lookup:
        """Resolve each setting from the argument, then the model, then settings.

        ``display_id`` is dropped when the model has no prefix, so a display ID
        for one model can't match a row in another model that shares UUIDs.
        ``slug`` is dropped when the model has no slug field. If that leaves
        nothing to try, the configuration can never match anything, so it
        raises instead of treating every identifier as not found.

        Raises:
            ValueError: If the prefix is not 1-16 lowercase letters.
            MissingPrefixError: If only ``display_id`` (and unusable
                strategies) were requested for a model without a prefix.
            ImproperlyConfigured: If only ``slug`` was requested for a model
                without the slug field.
        """
        prefix = _resolve_prefix(model, prefix)
        slug_field = _resolve_slug_field(model, slug_field)
        if strategies is None:
            strategies = get_setting("STRATEGIES")  # type: ignore[assignment]
        assert strategies is not None
        requested = strategies

        if prefix is None:
            strategies = tuple(s for s in strategies if s != "display_id")
        try:
            model._meta.get_field(slug_field)
        except FieldDoesNotExist:
            strategies = tuple(s for s in strategies if s != "slug")

        if requested and not strategies:
            if "display_id" in requested and prefix is None:
                raise MissingPrefixError(model_name=model.__name__)
            raise ImproperlyConfigured(
                f"Cannot lookup by slug: {model.__name__} has no {slug_field!r} field"
            )
        return cls(
            model.__name__,
            prefix,
            _resolve_uuid_field(model, uuid_field),
            slug_field,
            strategies,
        )

    def build(self, value: str | uuid.UUID) -> dict[str, Any]:
        """Turn an identifier into keyword arguments for ``QuerySet.get()``.

        Returns ``{uuid_field: UUID}`` for a display ID or UUID, or
        ``{slug_field: slug}`` for a slug.

        Raises:
            InvalidIdentifierError: If no strategy can parse the identifier.
            UnknownPrefixError: If a display ID has the wrong prefix.
        """
        result = parse_identifier(value, self.strategies, expected_prefix=self.prefix)
        if result.strategy == "slug":
            return {self.slug_field: result.slug}
        return {self.uuid_field: result.uuid}

    def build_many(
        self, values: Iterable[str | uuid.UUID]
    ) -> dict[str | uuid.UUID, tuple[str, Any]]:
        """Build a ``(field, value)`` pair for each identifier that parses.

        Identifiers ``build()`` rejects are left out, since they can't match
        a row.
        """
        built = {}
        for value in values:
            try:
                ((field, field_value),) = self.build(value).items()
            except DisplayIDLookupError:
                continue
            built[value] = (field, field_value)
        return built

    def filter_many(self, built: Iterable[tuple[str, Any]]) -> Q | None:
        """One ``__in`` filter per field, or None if there's nothing to match.

        None, because an empty ``Q()`` would match every row.
        """
        by_field: dict[str, list[Any]] = {}
        for field, field_value in built:
            by_field.setdefault(field, []).append(field_value)
        if not by_field:
            return None
        query = Q()
        for field, field_values in by_field.items():
            query |= Q(**{f"{field}__in": field_values})
        return query

    def fetch_many(
        self, queryset: QuerySet[M], values: Iterable[str | uuid.UUID]
    ) -> dict[str | uuid.UUID, M | None]:
        """Map each identifier to its row in *queryset*, or None, in one query.

        Raises:
            AmbiguousIdentifierError: If a slug matches more than one row.
        """
        values = list(values)
        built = self.build_many(values)
        query = self.filter_many(built.values())
        rows: dict[tuple[str, Any], list[M]] = {}
        if query is not None:
            fields = {field for field, _ in built.values()}
            for obj in queryset.filter(query):
                for field in fields:
                    rows.setdefault((field, getattr(obj, field)), []).append(obj)

        result: dict[str | uuid.UUID, M | None] = {}
        for value in values:
            matches = rows.get(built[value], []) if value in built else []
            if len(matches) > 1:
                raise AmbiguousIdentifierError(str(value), len(matches))
            result[value] = matches[0] if matches else None
        return result

    def require_prefix(self) -> str:
        """Return the prefix, or raise if the model can't have display IDs.

        Raises:
            MissingPrefixError: If there is no prefix.
        """
        if self.prefix is None:
            raise MissingPrefixError(model_name=self.model_name)
        return self.prefix

    def encode(self, uuid_value: uuid.UUID | str) -> str:
        """Turn a UUID into this model's display ID, the reverse of ``build()``.

        Raises:
            MissingPrefixError: If there is no prefix.
        """
        return encode_display_id(self.require_prefix(), uuid_value)


class _LookupOptions:
    """Lookup attributes shared by the view mixins and the admin mixin."""

    lookup_strategies: tuple[StrategyName, ...] | None = None
    display_id_prefix: str | None = None
    uuid_field: str | None = None
    slug_field: str | None = None

    def _get_lookup(self, model: type[models.Model]) -> _Lookup:
        return _Lookup.for_model(
            model,
            strategies=self.lookup_strategies,
            prefix=self.display_id_prefix,
            uuid_field=self.uuid_field,
            slug_field=self.slug_field,
        )


def _queryset_for(model: type[M], queryset: QuerySet[M] | None) -> QuerySet[M]:
    if queryset is None:
        return model._default_manager.all()
    if queryset.model is not model:
        raise TypeError(
            f"queryset must be for {model.__name__}, "
            f"got queryset for {queryset.model.__name__}"
        )
    return queryset


def resolve_object(
    model: type[M],
    value: str | uuid.UUID,
    *,
    strategies: tuple[StrategyName, ...] | None = None,
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
            or a UUID instance for direct UUID lookup. A UUID instance
            skips *strategies*, which only apply to strings. Strategies that
            can never be used for the model still raise, whatever the value.
        strategies: Tuple of strategy names to try in order. When ``None``
            (the default), uses the ``DISPLAY_IDS["STRATEGIES"]`` setting.
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
    qs = _queryset_for(model, queryset)
    lookup = _Lookup.for_model(
        model,
        strategies=strategies,
        prefix=prefix,
        uuid_field=uuid_field,
        slug_field=slug_field,
    ).build(value)

    try:
        return qs.get(**lookup)
    except model.DoesNotExist:  # type: ignore[attr-defined]
        raise ObjectNotFoundError(str(value), model_name=model.__name__) from None
    except model.MultipleObjectsReturned:  # type: ignore[attr-defined]
        count = qs.filter(**lookup).count()
        raise AmbiguousIdentifierError(str(value), count) from None


def resolve_objects(
    model: type[M],
    values: Iterable[str | uuid.UUID],
    *,
    strategies: tuple[StrategyName, ...] | None = None,
    prefix: str | None = None,
    uuid_field: str | None = None,
    slug_field: str | None = None,
    queryset: QuerySet[M] | None = None,
) -> dict[str | uuid.UUID, M | None]:
    """Resolve many identifiers in one query.

    Takes the same options as ``resolve_object()``. Each value is read the
    same way, but a value that doesn't parse, has the wrong prefix or has no
    row maps to ``None`` instead of raising.

    Returns:
        A dict from each input value to its object, or ``None``.

    Raises:
        AmbiguousIdentifierError: If a slug matches more than one object.
        TypeError: If queryset is not for the specified model.

    Example:
        found = resolve_objects(Invoice, ["inv_2aUyqjCzEIiEcYMKj7TZtw", "nope"])
        found["inv_2aUyqjCzEIiEcYMKj7TZtw"]  # the invoice
        found["nope"]  # None
    """
    qs = _queryset_for(model, queryset)
    lookup = _Lookup.for_model(
        model,
        strategies=strategies,
        prefix=prefix,
        uuid_field=uuid_field,
        slug_field=slug_field,
    )
    return lookup.fetch_many(qs, values)
