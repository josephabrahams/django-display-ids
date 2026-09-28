"""Lookup strategies for resolving identifiers to UUIDs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .encoding import decode_display_id, parse_uuid_string
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


def parse_uuid(value: str | uuid.UUID) -> StrategyResult | None:
    """Attempt to parse a value as a UUID.

    Accepts the standard hyphenated form (8-4-4-4-12) of any UUID version, in
    either case. Other forms, such as 32 hex digits without hyphens, aren't
    treated as UUIDs, so they can't be mistaken for slugs or vice versa. A
    ``uuid.UUID`` object is returned as-is.

    Args:
        value: The identifier string, or a UUID object.

    Returns:
        StrategyResult if valid UUID, None otherwise.
    """
    if isinstance(value, uuid.UUID):
        return StrategyResult(strategy="uuid", uuid=value)
    if not isinstance(value, str):
        return None
    try:
        return StrategyResult(strategy="uuid", uuid=parse_uuid_string(value))
    except ValueError:
        return None


def parse_display_id(
    value: str | uuid.UUID,
    *,
    expected_prefix: str | None = None,
) -> StrategyResult | None:
    """Attempt to parse a value as a display ID.

    Args:
        value: The identifier string. Anything else, including a UUID
            object, is not a display ID and returns None.
        expected_prefix: If provided, the prefix must match.

    Returns:
        StrategyResult if valid display ID, None otherwise.

    Raises:
        UnknownPrefixError: If expected_prefix is set and doesn't match.
    """
    if not isinstance(value, str):
        return None
    try:
        prefix, parsed_uuid = decode_display_id(value)
    except ValueError:
        return None

    if expected_prefix is not None and prefix != expected_prefix:
        raise UnknownPrefixError(value, actual=prefix, expected=expected_prefix)

    return StrategyResult(strategy="display_id", uuid=parsed_uuid, prefix=prefix)


def parse_slug(value: str | uuid.UUID) -> StrategyResult | None:
    """Attempt to parse a value as a slug.

    Slugs are accepted as-is without validation. The caller is
    responsible for determining if the model supports slug lookup.

    Args:
        value: The identifier string. Anything else, including a UUID
            object, is not a slug and returns None.

    Returns:
        StrategyResult with the slug value, or None for an empty string.
    """
    # Accept any non-empty string as a potential slug
    if not isinstance(value, str) or not value:
        return None
    return StrategyResult(strategy="slug", slug=value)


def parse_identifier(
    value: str | uuid.UUID,
    strategies: tuple[StrategyName, ...],
    *,
    expected_prefix: str | None = None,
) -> StrategyResult:
    """Parse an identifier using the specified strategies in order.

    Leading and trailing whitespace is stripped first.

    A ``uuid.UUID`` object is already parsed, so it is returned as a
    ``"uuid"`` result without checking *strategies*. Strategies describe
    which text formats to accept, and a UUID object isn't text.

    Args:
        value: The identifier string, or a UUID object.
        strategies: Tuple of strategy names to try in order.
        expected_prefix: For display_id strategy, the expected prefix.
            If None, any valid display ID prefix is accepted.

    Returns:
        StrategyResult from the first matching strategy.

    Raises:
        InvalidIdentifierError: If no strategy matches.
        UnknownPrefixError: If display_id prefix doesn't match expected.
    """
    if isinstance(value, uuid.UUID):
        return StrategyResult(strategy="uuid", uuid=value)

    value = value.strip()

    for strategy in strategies:
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
        f"Could not parse {value!r} using strategies: {', '.join(strategies)}",
    )
