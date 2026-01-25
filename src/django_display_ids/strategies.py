"""Lookup strategies for resolving identifiers to UUIDs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .encoding import decode_display_id
from .exceptions import InvalidIdentifierError, UnknownPrefixError

if TYPE_CHECKING:
    from .typing import StrategyName

__all__ = [
    "StrategyResult",
    "parse_display_id",
    "parse_identifier",
    "parse_slug",
    "parse_uuid",
]


@dataclass(frozen=True, slots=True)
class StrategyResult:
    """Result of a successful strategy parse.

    Attributes:
        strategy: The strategy that matched.
        uuid: The resolved UUID (if applicable).
        slug: The slug value (if strategy is "slug").
        prefix: The display ID prefix (if strategy is "display_id").
    """

    strategy: StrategyName
    uuid: uuid.UUID | None = None
    slug: str | None = None
    prefix: str | None = None


def parse_uuid(value: str) -> StrategyResult | None:
    """Attempt to parse a value as a UUID.

    Accepts UUIDv4 and UUIDv7 in standard hyphenated or unhyphenated format.

    Args:
        value: The identifier string.

    Returns:
        StrategyResult if valid UUID, None otherwise.
    """
    try:
        parsed = uuid.UUID(value)
        return StrategyResult(strategy="uuid", uuid=parsed)
    except (ValueError, AttributeError):
        return None


def parse_display_id(
    value: str,
    *,
    expected_prefix: str | None = None,
) -> StrategyResult | None:
    """Attempt to parse a value as a display ID.

    Args:
        value: The identifier string.
        expected_prefix: If provided, the prefix must match.

    Returns:
        StrategyResult if valid display ID, None otherwise.

    Raises:
        UnknownPrefixError: If expected_prefix is set and doesn't match.
    """
    try:
        prefix, parsed_uuid = decode_display_id(value)
    except ValueError:
        return None

    if expected_prefix is not None and prefix != expected_prefix:
        raise UnknownPrefixError(value, actual=prefix, expected=expected_prefix)

    return StrategyResult(strategy="display_id", uuid=parsed_uuid, prefix=prefix)


def parse_slug(value: str) -> StrategyResult | None:
    """Attempt to parse a value as a slug.

    Slugs are accepted as-is without validation. The caller is
    responsible for determining if the model supports slug lookup.

    Args:
        value: The identifier string.

    Returns:
        StrategyResult with the slug value.
    """
    # Accept any non-empty string as a potential slug
    if not value:
        return None
    return StrategyResult(strategy="slug", slug=value)


def parse_identifier(
    value: str,
    strategies: tuple[StrategyName, ...],
    *,
    expected_prefix: str | None = None,
) -> StrategyResult:
    """Parse an identifier using the specified strategies in order.

    Args:
        value: The identifier string.
        strategies: Tuple of strategy names to try in order.
        expected_prefix: For display_id strategy, the expected prefix.
            If None, the display_id strategy is skipped.

    Returns:
        StrategyResult from the first matching strategy.

    Raises:
        InvalidIdentifierError: If no strategy matches.
        UnknownPrefixError: If display_id prefix doesn't match expected.
    """
    # Filter out display_id strategy if no prefix is configured.
    # This prevents cross-model lookups where a display ID for one model
    # could accidentally match a UUID in another model.
    effective_strategies = tuple(
        s for s in strategies if s != "display_id" or expected_prefix is not None
    )

    if not effective_strategies:
        raise InvalidIdentifierError(
            value,
            f"No strategies available to parse identifier {value!r} "
            "(display_id strategy requires a prefix)",
        )

    for strategy in effective_strategies:
        result: StrategyResult | None = None

        if strategy == "uuid":
            result = parse_uuid(value)
        elif strategy == "display_id":
            result = parse_display_id(value, expected_prefix=expected_prefix)
        elif strategy == "slug":
            result = parse_slug(value)

        if result is not None:
            return result

    raise InvalidIdentifierError(
        value,
        f"Could not parse {value!r} using strategies: {', '.join(effective_strategies)}",
    )
