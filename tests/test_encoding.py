"""Tests for encoding module."""

import uuid

import pytest

from django_display_ids.encoding import (
    ALPHABET,
    ENCODED_UUID_LENGTH,
    decode_display_id,
    decode_uuid,
    encode_display_id,
    encode_uuid,
)


class TestEncodeUuid:
    """Tests for encode_uuid function."""

    def test_returns_22_characters(self):
        """Encoded UUID is always 22 characters."""
        test_uuid = uuid.uuid4()
        encoded = encode_uuid(test_uuid)
        assert len(encoded) == ENCODED_UUID_LENGTH

    def test_uses_base62_alphabet(self):
        """Encoded string only contains base62 characters."""
        test_uuid = uuid.uuid4()
        encoded = encode_uuid(test_uuid)
        assert all(char in ALPHABET for char in encoded)

    def test_known_value(self):
        """Pinned so a change to the encoding can't slip through.

        This is the example used throughout the docs.
        """
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert encode_uuid(test_uuid) == "2aUyqjCzEIiEcYMKj7TZtw"

    def test_zero_uuid(self):
        """Zero UUID encodes correctly (all zeros should be 22 zeros)."""
        zero_uuid = uuid.UUID(int=0)
        encoded = encode_uuid(zero_uuid)
        assert len(encoded) == ENCODED_UUID_LENGTH
        assert encoded == "0" * ENCODED_UUID_LENGTH

    def test_max_uuid(self):
        """Maximum UUID encodes correctly."""
        max_uuid = uuid.UUID(int=(2**128) - 1)
        encoded = encode_uuid(max_uuid)
        assert len(encoded) == ENCODED_UUID_LENGTH


class TestDecodeUuid:
    """Tests for decode_uuid function."""

    def test_round_trip_many(self):
        """Round trip works for many UUIDs."""
        for _ in range(100):
            original = uuid.uuid4()
            encoded = encode_uuid(original)
            decoded = decode_uuid(encoded)
            assert decoded == original

    @pytest.mark.parametrize("value", ["abc", "a" * 30])
    def test_invalid_length(self, value):
        with pytest.raises(ValueError, match="Expected 22 characters"):
            decode_uuid(value)

    @pytest.mark.parametrize("char", ["!", "_"])
    def test_invalid_character(self, char):
        with pytest.raises(ValueError, match="Invalid base62 character"):
            decode_uuid(char + "0" * 21)

    def test_overflow_value(self):
        """Value exceeding UUID range raises ValueError."""
        # Maximum valid base62 for 128 bits is less than 'z' * 22
        # This should overflow
        with pytest.raises(ValueError, match="exceeds UUID range"):
            decode_uuid("z" * 22)

    def test_known_value(self):
        assert decode_uuid("2aUyqjCzEIiEcYMKj7TZtw") == uuid.UUID(
            "550e8400-e29b-41d4-a716-446655440000"
        )


class TestEncodeDisplayId:
    """Tests for encode_display_id function."""

    def test_format(self):
        """Display ID has correct format: prefix_base62."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)
        assert display_id.startswith("inv_")
        assert len(display_id) == 3 + 1 + ENCODED_UUID_LENGTH  # prefix + _ + base62

    def test_known_value(self):
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert encode_display_id("inv", test_uuid) == "inv_2aUyqjCzEIiEcYMKj7TZtw"

    @pytest.mark.parametrize("prefix", ["INV", "inv1", "inv_", "", "a" * 17])
    def test_invalid_prefix(self, prefix):
        with pytest.raises(ValueError, match="must be 1-16 lowercase letters"):
            encode_display_id(prefix, uuid.uuid4())


class TestDecodeDisplayId:
    @pytest.mark.parametrize(
        "prefix", ["a", "ab", "inv", "product", "abcdefghijklmnop"]
    )
    def test_round_trip(self, prefix):
        test_uuid = uuid.uuid4()
        assert decode_display_id(encode_display_id(prefix, test_uuid)) == (
            prefix,
            test_uuid,
        )

    @pytest.mark.parametrize(
        "value",
        [
            "inv1234567890123456789012",  # no underscore
            "inv_abc",  # encoded part too short
            "INV_" + "0" * 22,  # uppercase prefix
        ],
    )
    def test_invalid_format(self, value):
        with pytest.raises(ValueError, match="Invalid display ID format"):
            decode_display_id(value)


class TestShortUuidCompatibility:
    """Cross-check the base62 encoding against the shortuuid library."""

    @pytest.fixture
    def shortuuid(self):
        """A ShortUUID with our alphabet. shortuuid drops leading zeros, so
        its output is padded to our fixed length."""
        shortuuid = pytest.importorskip("shortuuid")
        return shortuuid.ShortUUID(alphabet=ALPHABET)

    def test_encoding_matches(self, shortuuid):
        for _ in range(100):
            value = uuid.uuid4()
            expected = shortuuid.encode(value).zfill(ENCODED_UUID_LENGTH)
            assert encode_uuid(value) == expected, f"Mismatch for UUID {value}"

    def test_decodes_shortuuid_output(self, shortuuid):
        value = uuid.uuid4()
        assert decode_uuid(shortuuid.encode(value).zfill(ENCODED_UUID_LENGTH)) == value


class TestEncodeAcceptsStrings:
    """Encoders accept UUID strings in the same form the lookup side accepts."""

    value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.parametrize(
        "text",
        [
            "550e8400-e29b-41d4-a716-446655440000",
            "550E8400-E29B-41D4-A716-446655440000",
            " 550e8400-e29b-41d4-a716-446655440000 ",
        ],
    )
    def test_string_matches_uuid_object(self, text):
        assert encode_uuid(text) == encode_uuid(self.value)
        assert encode_display_id("inv", text) == encode_display_id("inv", self.value)

    @pytest.mark.parametrize(
        "text",
        [
            "not-a-uuid",
            "550e8400e29b41d4a716446655440000",
            "{550e8400-e29b-41d4-a716-446655440000}",
            "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
        ],
    )
    def test_invalid_string_raises_value_error(self, text):
        with pytest.raises(ValueError, match="Invalid UUID"):
            encode_uuid(text)

    def test_other_types_raise_type_error(self):
        with pytest.raises(TypeError, match="got int"):
            encode_uuid(12345)
