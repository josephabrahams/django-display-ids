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

    def test_deterministic(self):
        """Same UUID always produces same encoding."""
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert encode_uuid(test_uuid) == encode_uuid(test_uuid)

    def test_different_uuids_produce_different_encodings(self):
        """Different UUIDs produce different encodings."""
        uuid1 = uuid.uuid4()
        uuid2 = uuid.uuid4()
        assert encode_uuid(uuid1) != encode_uuid(uuid2)

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

    def test_uuidv7_produces_22_chars(self):
        """UUIDv7 (timestamp-based) always produces 22 chars.

        UUIDv7 has timestamp in high bits, so it will never have
        leading zeros that could be stripped.
        """
        # Simulate a UUIDv7-like UUID (high bits set due to timestamp)
        # UUIDv7 format: 48-bit timestamp + 4-bit version + random
        import time

        timestamp_ms = int(time.time() * 1000)
        timestamp_bits = timestamp_ms << 80
        version_bits = 7 << 76  # Version 7
        random_bits = uuid.uuid4().int & ((1 << 76) - 1)
        uuidv7_int = timestamp_bits | version_bits | random_bits
        # Ensure it fits in 128 bits
        uuidv7_int = uuidv7_int & ((1 << 128) - 1)
        uuidv7 = uuid.UUID(int=uuidv7_int)

        encoded = encode_uuid(uuidv7)
        assert len(encoded) == ENCODED_UUID_LENGTH


class TestDecodeUuid:
    """Tests for decode_uuid function."""

    def test_round_trip(self):
        """Encoding then decoding returns original UUID."""
        original = uuid.uuid4()
        encoded = encode_uuid(original)
        decoded = decode_uuid(encoded)
        assert decoded == original

    def test_round_trip_many(self):
        """Round trip works for many UUIDs."""
        for _ in range(100):
            original = uuid.uuid4()
            encoded = encode_uuid(original)
            decoded = decode_uuid(encoded)
            assert decoded == original

    def test_invalid_length_short(self):
        """Decoding string with wrong length raises ValueError."""
        with pytest.raises(ValueError, match="Expected 22 characters"):
            decode_uuid("abc")

    def test_invalid_length_long(self):
        """Decoding too-long string raises ValueError."""
        with pytest.raises(ValueError, match="Expected 22 characters"):
            decode_uuid("a" * 30)

    def test_invalid_character(self):
        """Decoding string with invalid character raises ValueError."""
        with pytest.raises(ValueError, match="Invalid base62 character"):
            decode_uuid("!" + "0" * 21)

    def test_invalid_character_special(self):
        """Special characters are rejected."""
        with pytest.raises(ValueError, match="Invalid base62 character"):
            decode_uuid("_" + "0" * 21)

    def test_overflow_value(self):
        """Value exceeding UUID range raises ValueError."""
        # Maximum valid base62 for 128 bits is less than 'z' * 22
        # This should overflow
        with pytest.raises(ValueError, match="exceeds UUID range"):
            decode_uuid("z" * 22)

    def test_known_value(self):
        """Decoding a known encoded value works."""
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        encoded = encode_uuid(test_uuid)
        decoded = decode_uuid(encoded)
        assert decoded == test_uuid


class TestEncodeDisplayId:
    """Tests for encode_display_id function."""

    def test_format(self):
        """Display ID has correct format: prefix_base62."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)
        assert display_id.startswith("inv_")
        assert len(display_id) == 3 + 1 + ENCODED_UUID_LENGTH  # prefix + _ + base62

    def test_valid_prefixes(self):
        """Various valid prefixes are accepted."""
        test_uuid = uuid.uuid4()
        valid_prefixes = ["a", "inv", "product", "abcdefghijklmnop"]  # 16 chars max
        for prefix in valid_prefixes:
            display_id = encode_display_id(prefix, test_uuid)
            assert display_id.startswith(f"{prefix}_")

    def test_invalid_prefix_uppercase(self):
        """Uppercase prefix raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-16 lowercase letters"):
            encode_display_id("INV", uuid.uuid4())

    def test_invalid_prefix_numbers(self):
        """Prefix with numbers raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-16 lowercase letters"):
            encode_display_id("inv1", uuid.uuid4())

    def test_invalid_prefix_underscore(self):
        """Prefix with underscore raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-16 lowercase letters"):
            encode_display_id("inv_", uuid.uuid4())

    def test_invalid_prefix_empty(self):
        """Empty prefix raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-16 lowercase letters"):
            encode_display_id("", uuid.uuid4())

    def test_invalid_prefix_too_long(self):
        """Prefix longer than 16 chars raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-16 lowercase letters"):
            encode_display_id("a" * 17, uuid.uuid4())


class TestDecodeDisplayId:
    """Tests for decode_display_id function."""

    def test_round_trip(self):
        """Encoding then decoding returns original prefix and UUID."""
        test_uuid = uuid.uuid4()
        display_id = encode_display_id("inv", test_uuid)
        prefix, decoded_uuid = decode_display_id(display_id)
        assert prefix == "inv"
        assert decoded_uuid == test_uuid

    def test_invalid_format_no_underscore(self):
        """Missing underscore raises ValueError."""
        with pytest.raises(ValueError, match="Invalid display ID format"):
            decode_display_id("inv1234567890123456789012")

    def test_invalid_format_wrong_base62_length(self):
        """Wrong base62 length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid display ID format"):
            decode_display_id("inv_abc")

    def test_invalid_format_uppercase_prefix(self):
        """Uppercase prefix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid display ID format"):
            decode_display_id("INV_" + "0" * 22)

    def test_various_prefixes(self):
        """Various prefix lengths work correctly."""
        test_uuid = uuid.uuid4()
        for prefix in ["a", "ab", "inv", "product", "abcdefghijklmnop"]:
            display_id = encode_display_id(prefix, test_uuid)
            decoded_prefix, decoded_uuid = decode_display_id(display_id)
            assert decoded_prefix == prefix
            assert decoded_uuid == test_uuid


class TestShortUuidCompatibility:
    """Tests validating base62 encoding against shortuuid library.

    These tests use shortuuid with our alphabet to validate that
    our encoding produces correct results.
    """

    @pytest.fixture
    def shortuuid_module(self):
        """Get shortuuid module configured with our alphabet."""
        pytest.importorskip("shortuuid")
        import shortuuid

        shortuuid.set_alphabet(ALPHABET)
        return shortuuid

    def test_encoding_matches_shortuuid(self, shortuuid_module):
        """Our encoding matches shortuuid with same alphabet (padded)."""
        test_uuid = uuid.uuid4()

        our_encoded = encode_uuid(test_uuid)
        shortuuid_encoded = shortuuid_module.encode(test_uuid)
        # Pad shortuuid output to 22 chars (it strips leading zeros)
        shortuuid_padded = shortuuid_encoded.zfill(ENCODED_UUID_LENGTH)

        assert our_encoded == shortuuid_padded

    def test_encoding_matches_many_uuids(self, shortuuid_module):
        """Encoding matches for many random UUIDs."""
        for _ in range(100):
            test_uuid = uuid.uuid4()

            our_encoded = encode_uuid(test_uuid)
            shortuuid_encoded = shortuuid_module.encode(test_uuid)
            shortuuid_padded = shortuuid_encoded.zfill(ENCODED_UUID_LENGTH)

            assert our_encoded == shortuuid_padded, f"Mismatch for UUID {test_uuid}"

    def test_decoding_shortuuid_output(self, shortuuid_module):
        """We can decode shortuuid output (padded)."""
        test_uuid = uuid.uuid4()

        shortuuid_encoded = shortuuid_module.encode(test_uuid)
        shortuuid_padded = shortuuid_encoded.zfill(ENCODED_UUID_LENGTH)

        decoded = decode_uuid(shortuuid_padded)
        assert decoded == test_uuid

    def test_known_uuid_value(self, shortuuid_module):
        """Test with a known UUID value."""
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

        our_encoded = encode_uuid(test_uuid)
        shortuuid_encoded = shortuuid_module.encode(test_uuid)
        shortuuid_padded = shortuuid_encoded.zfill(ENCODED_UUID_LENGTH)

        assert our_encoded == shortuuid_padded
