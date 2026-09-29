"""Base62 encoding/decoding for UUIDs and display IDs."""

from __future__ import annotations

import re
import uuid

from django.urls.converters import UUIDConverter

__all__ = [
    "decode_display_id",
    "decode_uuid",
    "encode_display_id",
    "encode_uuid",
    "parse_uuid_string",
]

# Base62 alphabet: 0-9, A-Z, a-z
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(ALPHABET)

# A UUID is 128 bits, which requires ceil(128 * log(2) / log(62)) = 22 base62 characters
ENCODED_UUID_LENGTH = 22

# Display ID format: {prefix}_{base62(uuid)}
# Prefix must be lowercase letters only, 1-16 chars
PREFIX_REGEX = r"[a-z]{1,16}"
ENCODED_UUID_REGEX = rf"[0-9A-Za-z]{{{ENCODED_UUID_LENGTH}}}"
DISPLAY_ID_REGEX = rf"{PREFIX_REGEX}_{ENCODED_UUID_REGEX}"

# The only UUID string format accepted anywhere: Django's <uuid:> pattern
# (8-4-4-4-12 with hyphens) in either case. Forms like 32 hex digits without
# hyphens, braces or urn:uuid: aren't accepted, because they're too easy to
# confuse with other strings, such as slugs made from MD5 hashes.
UUID_REGEX = rf"(?i:{UUIDConverter.regex})"

PREFIX_PATTERN = re.compile(rf"^{PREFIX_REGEX}$")
DISPLAY_ID_PATTERN = re.compile(rf"^({PREFIX_REGEX})_({ENCODED_UUID_REGEX})$")
UUID_PATTERN = re.compile(rf"^{UUID_REGEX}$")


def parse_uuid_string(value: str) -> uuid.UUID:
    """Parse a UUID string in the standard hyphenated form, in either case.

    Raises:
        ValueError: If *value* isn't 8-4-4-4-12 hex digits with hyphens.
    """
    if not UUID_PATTERN.match(value):
        raise ValueError(f"Invalid UUID: {value!r}")
    return uuid.UUID(value)


def _to_uuid(value: uuid.UUID | str) -> uuid.UUID:
    """Return *value* as a UUID object, parsing strings with ``parse_uuid_string``."""
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        return parse_uuid_string(value.strip())
    raise TypeError(f"Expected a UUID or string, got {type(value).__name__}")


def encode_uuid(value: uuid.UUID | str) -> str:
    """Encode a UUID to a fixed-length base62 string.

    Args:
        value: UUID to encode, as a UUID object or a hyphenated UUID
            string in either case.

    Returns:
        22-character base62 string.

    Raises:
        ValueError: If a string isn't a valid UUID.
        TypeError: If value is neither a UUID nor a string.
    """
    num = _to_uuid(value).int
    chars = []

    for _ in range(ENCODED_UUID_LENGTH):
        num, remainder = divmod(num, BASE)
        chars.append(ALPHABET[remainder])

    # Reverse to get most significant digit first
    return "".join(reversed(chars))


def decode_uuid(value: str) -> uuid.UUID:
    """Decode a base62 string to a UUID.

    Args:
        value: 22-character base62 string.

    Returns:
        Decoded UUID.

    Raises:
        ValueError: If the string is not a valid base62-encoded UUID.
    """
    if len(value) != ENCODED_UUID_LENGTH:
        raise ValueError(f"Expected {ENCODED_UUID_LENGTH} characters, got {len(value)}")

    num = 0
    for char in value:
        try:
            digit = ALPHABET.index(char)
        except ValueError:
            raise ValueError(f"Invalid base62 character: {char!r}") from None
        num = num * BASE + digit

    # Validate the number fits in 128 bits
    if num.bit_length() > 128:
        raise ValueError("Decoded value exceeds UUID range")

    return uuid.UUID(int=num)


def encode_display_id(prefix: str, value: uuid.UUID | str) -> str:
    """Encode a UUID to a display ID with prefix.

    Args:
        prefix: Lowercase letter prefix (1-16 chars).
        value: UUID to encode, as a UUID object or a hyphenated UUID
            string in either case.

    Returns:
        Display ID in format {prefix}_{base62(uuid)}.

    Raises:
        ValueError: If prefix is invalid or a string isn't a valid UUID.
        TypeError: If value is neither a UUID nor a string.
    """
    if not PREFIX_PATTERN.match(prefix):
        raise ValueError(f"Prefix must be 1-16 lowercase letters, got: {prefix!r}")

    return f"{prefix}_{encode_uuid(value)}"


def decode_display_id(value: str) -> tuple[str, uuid.UUID]:
    """Decode a display ID to its prefix and UUID.

    Args:
        value: Display ID in format {prefix}_{base62(uuid)}.

    Returns:
        Tuple of (prefix, uuid).

    Raises:
        ValueError: If the display ID format is invalid.
    """
    match = DISPLAY_ID_PATTERN.match(value)
    if not match:
        raise ValueError(f"Invalid display ID format: {value!r}")

    prefix, encoded = match.groups()
    return prefix, decode_uuid(encoded)
