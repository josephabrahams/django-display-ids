"""Tests for examples module."""

import uuid

import pytest

from django_display_ids.encoding import ENCODED_UUID_LENGTH, decode_display_id
from django_display_ids.examples import (
    example_display_id,
    example_display_id_for_prefix,
    example_uuid,
    example_uuid_for_prefix,
)

from .models import Invoice, Order


class TestExampleUuid:
    """Tests for example_uuid function."""

    def test_returns_uuid(self):
        """Returns a UUID instance."""
        result = example_uuid("inv")
        assert isinstance(result, uuid.UUID)

    def test_deterministic_same_prefix(self):
        """Same prefix always produces same UUID."""
        uuid1 = example_uuid("inv")
        uuid2 = example_uuid("inv")
        assert uuid1 == uuid2

    def test_different_prefixes_produce_different_uuids(self):
        """Different prefixes produce different UUIDs."""
        uuid_inv = example_uuid("inv")
        uuid_user = example_uuid("user")
        uuid_prod = example_uuid("prod")

        assert uuid_inv != uuid_user
        assert uuid_inv != uuid_prod
        assert uuid_user != uuid_prod

    def test_accepts_model_class(self):
        """Can accept a model class with display_id_prefix."""
        result = example_uuid(Invoice)
        assert isinstance(result, uuid.UUID)
        # Should be same as using the prefix directly
        assert result == example_uuid("inv")

    def test_model_without_prefix_raises(self):
        """Model without display_id_prefix raises ValueError."""
        with pytest.raises(ValueError, match="has no display_id_prefix"):
            example_uuid(Order)


class TestExampleDisplayId:
    """Tests for example_display_id function."""

    def test_returns_string(self):
        """Returns a string."""
        result = example_display_id("inv")
        assert isinstance(result, str)

    def test_format_correct(self):
        """Display ID has correct format."""
        result = example_display_id("inv")
        assert result.startswith("inv_")
        # Total length: prefix + underscore + 22 char base62
        assert len(result) == 3 + 1 + ENCODED_UUID_LENGTH

    def test_deterministic_same_prefix(self):
        """Same prefix always produces same display ID."""
        display_id1 = example_display_id("inv")
        display_id2 = example_display_id("inv")
        assert display_id1 == display_id2

    def test_different_prefixes_produce_different_display_ids(self):
        """Different prefixes produce different display IDs."""
        id_inv = example_display_id("inv")
        id_user = example_display_id("user")
        id_prod = example_display_id("prod")

        assert id_inv != id_user
        assert id_inv != id_prod
        assert id_user != id_prod

    def test_accepts_model_class(self):
        """Can accept a model class with display_id_prefix."""
        result = example_display_id(Invoice)
        assert result.startswith("inv_")
        # Should be same as using the prefix directly
        assert result == example_display_id("inv")

    def test_model_without_prefix_raises(self):
        """Model without display_id_prefix raises ValueError."""
        with pytest.raises(ValueError, match="has no display_id_prefix"):
            example_display_id(Order)

    def test_decodable(self):
        """Generated display ID can be decoded."""
        display_id = example_display_id("inv")
        prefix, decoded_uuid = decode_display_id(display_id)

        assert prefix == "inv"
        assert decoded_uuid == example_uuid("inv")

    def test_various_prefixes(self):
        """Works with various prefix lengths."""
        prefixes = ["a", "ab", "inv", "product", "abcdefghijklmnop"]
        for prefix in prefixes:
            display_id = example_display_id(prefix)
            assert display_id.startswith(f"{prefix}_")
            decoded_prefix, _ = decode_display_id(display_id)
            assert decoded_prefix == prefix


class TestAliases:
    """Tests for backwards-compatibility aliases."""

    def test_example_uuid_for_prefix_is_alias(self):
        """example_uuid_for_prefix is an alias for example_uuid."""
        assert example_uuid_for_prefix("inv") == example_uuid("inv")

    def test_example_display_id_for_prefix_is_alias(self):
        """example_display_id_for_prefix is an alias for example_display_id."""
        assert example_display_id_for_prefix("inv") == example_display_id("inv")
