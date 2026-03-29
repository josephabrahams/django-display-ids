"""Tests for strategies module."""

import uuid

import pytest

from django_display_ids.encoding import encode_display_id
from django_display_ids.exceptions import InvalidIdentifierError, UnknownPrefixError
from django_display_ids.strategies import (
    StrategyResult,
    parse_display_id,
    parse_identifier,
    parse_slug,
    parse_uuid,
)


class TestParseUuid:
    """Tests for parse_uuid function."""

    def test_valid_hyphenated_uuid(self):
        """Standard hyphenated UUID is parsed."""
        test_uuid = uuid.uuid4()
        result = parse_uuid(str(test_uuid))

        assert result is not None
        assert result.strategy == "uuid"
        assert result.uuid == test_uuid

    def test_valid_unhyphenated_uuid(self):
        """Unhyphenated UUID is parsed."""
        test_uuid = uuid.uuid4()
        result = parse_uuid(test_uuid.hex)

        assert result is not None
        assert result.strategy == "uuid"
        assert result.uuid == test_uuid

    def test_invalid_string(self):
        """Invalid string returns None."""
        assert parse_uuid("not-a-uuid") is None
        assert parse_uuid("inv_abc123") is None
        assert parse_uuid("") is None

    def test_display_id_not_parsed_as_uuid(self):
        """Display ID format is not parsed as UUID."""
        display_id = encode_display_id("inv", uuid.uuid4())
        result = parse_uuid(display_id)
        assert result is None


class TestParseDisplayId:
    """Tests for parse_display_id function."""

    def test_valid_display_id(self):
        """Valid display ID is parsed."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        result = parse_display_id(display_id)

        assert result is not None
        assert result.strategy == "display_id"
        assert result.uuid == test_uuid
        assert result.prefix == "inv"

    def test_valid_display_id_with_expected_prefix(self):
        """Display ID with matching expected prefix is parsed."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        result = parse_display_id(display_id, expected_prefix="inv")

        assert result is not None
        assert result.prefix == "inv"
        assert result.uuid == test_uuid

    def test_wrong_prefix_raises_error(self):
        """Display ID with wrong prefix raises UnknownPrefixError."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        with pytest.raises(UnknownPrefixError) as exc_info:
            parse_display_id(display_id, expected_prefix="prod")

        assert exc_info.value.actual == "inv"
        assert exc_info.value.expected == "prod"

    def test_invalid_format_returns_none(self):
        """Invalid display ID format returns None."""
        assert parse_display_id("not-a-display-id") is None
        assert parse_display_id("inv_short") is None
        assert parse_display_id("INV_" + "0" * 22) is None
        assert parse_display_id("") is None

    def test_uuid_not_parsed_as_display_id(self):
        """UUID format is not parsed as display ID."""
        test_uuid = uuid.uuid4()
        result = parse_display_id(str(test_uuid))
        assert result is None


class TestParseSlug:
    """Tests for parse_slug function."""

    def test_valid_slug(self):
        """Any non-empty string is accepted as slug."""
        result = parse_slug("my-product-slug")

        assert result is not None
        assert result.strategy == "slug"
        assert result.slug == "my-product-slug"

    def test_uuid_string_as_slug(self):
        """UUID string is accepted as slug (slug is catch-all)."""
        test_uuid = uuid.uuid4()
        result = parse_slug(str(test_uuid))

        assert result is not None
        assert result.strategy == "slug"
        assert result.slug == str(test_uuid)

    def test_display_id_as_slug(self):
        """Display ID is accepted as slug (slug is catch-all)."""
        display_id = encode_display_id("inv", uuid.uuid4())
        result = parse_slug(display_id)

        assert result is not None
        assert result.strategy == "slug"
        assert result.slug == display_id

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert parse_slug("") is None


class TestParseIdentifier:
    """Tests for parse_identifier function."""

    def test_uuid_first_strategy(self):
        """UUID is matched when uuid strategy is first."""
        test_uuid = uuid.uuid4()

        result = parse_identifier(
            str(test_uuid),
            strategies=("uuid", "display_id", "slug"),
            expected_prefix="inv",
        )

        assert result.strategy == "uuid"
        assert result.uuid == test_uuid

    def test_display_id_first_strategy(self):
        """Display ID is matched when display_id strategy is first."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        result = parse_identifier(
            display_id,
            strategies=("display_id", "uuid", "slug"),
            expected_prefix="inv",
        )

        assert result.strategy == "display_id"
        assert result.uuid == test_uuid
        assert result.prefix == "inv"

    def test_slug_fallback(self):
        """Slug is matched when other strategies don't match."""
        result = parse_identifier(
            "my-product-slug",
            strategies=("uuid", "display_id", "slug"),
            expected_prefix="inv",
        )

        assert result.strategy == "slug"
        assert result.slug == "my-product-slug"

    def test_display_id_without_prefix_accepts_any(self):
        """display_id strategy accepts any prefix when expected_prefix is None."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        result = parse_identifier(
            display_id,
            strategies=("display_id", "slug"),
            expected_prefix=None,
        )

        assert result.strategy == "display_id"
        assert result.uuid == test_uuid
        assert result.prefix == "inv"

    def test_display_id_only_without_prefix_parses_successfully(self):
        """display_id as only strategy without prefix still parses."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        result = parse_identifier(
            display_id,
            strategies=("display_id",),
            expected_prefix=None,
        )

        assert result.strategy == "display_id"
        assert result.uuid == test_uuid

    def test_no_match_raises_error(self):
        """No matching strategy raises InvalidIdentifierError."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            parse_identifier(
                "invalid",
                strategies=("uuid",),  # Only UUID, which won't match
            )

        assert "Could not parse" in str(exc_info.value)

    def test_wrong_prefix_raises_error(self):
        """Wrong prefix raises UnknownPrefixError."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        with pytest.raises(UnknownPrefixError):
            parse_identifier(
                display_id,
                strategies=("display_id", "uuid"),
                expected_prefix="prod",
            )

    def test_strategy_order_matters(self):
        """Strategies are tried in order."""
        test_uuid = uuid.uuid4()

        # With slug first, it catches everything
        result = parse_identifier(
            str(test_uuid),
            strategies=("slug", "uuid"),
        )
        assert result.strategy == "slug"

        # With uuid first, it matches the UUID
        result = parse_identifier(
            str(test_uuid),
            strategies=("uuid", "slug"),
        )
        assert result.strategy == "uuid"

    def test_default_strategies(self):
        """Default strategies work correctly."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)

        # display_id, uuid are default
        result = parse_identifier(
            display_id,
            strategies=("display_id", "uuid"),
            expected_prefix="inv",
        )
        assert result.strategy == "display_id"

        result = parse_identifier(
            str(test_uuid),
            strategies=("display_id", "uuid"),
            expected_prefix="inv",
        )
        assert result.strategy == "uuid"


class TestStrategyResult:
    """Tests for StrategyResult dataclass."""

    def test_frozen(self):
        """StrategyResult is immutable."""
        result = StrategyResult(strategy="uuid", uuid=uuid.uuid4())

        with pytest.raises(AttributeError):
            result.strategy = "slug"

    def test_slots(self):
        """StrategyResult uses slots."""
        result = StrategyResult(strategy="uuid")
        assert hasattr(result, "__slots__")

    def test_defaults(self):
        """Optional fields default to None."""
        result = StrategyResult(strategy="uuid")
        assert result.uuid is None
        assert result.slug is None
        assert result.prefix is None
