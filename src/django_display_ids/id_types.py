"""Display IDs that aren't backed by a model, like request IDs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

from . import registry
from .encoding import ENCODED_UUID_REGEX, PREFIX_PATTERN, encode_display_id
from .exceptions import DisplayIDLookupError
from .strategies import parse_identifier

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["DisplayIDType"]


class DisplayIDType:
    """A display ID format with a prefix but no model behind it.

    Example:
        RequestID = DisplayIDType("req")

        RequestID.generate()  # "req_..." from a new uuid7
        RequestID.encode(request_uid)  # "req_..." for a UUID you have
        RequestID.parse("req_2aUyqjCzEIiEcYMKj7TZtw")
        # UUID('550e8400-e29b-41d4-a716-446655440000')
        RequestID.is_valid("inv_2aUyqjCzEIiEcYMKj7TZtw")  # False

    Args:
        prefix: 1 to 16 lowercase letters. It can't be a model's prefix.
        factory: Makes the UUID for ``generate()``. Defaults to
            ``uuid.uuid7``, which needs Python 3.14+. On older versions,
            pass one, such as ``uuid6.uuid7``, or ``uuid.uuid4`` if the IDs
            shouldn't reveal when they were made.

    Raises:
        ValueError: If the prefix is invalid or a model already uses it.
    """

    def __init__(
        self, prefix: str, *, factory: Callable[[], uuid.UUID] | None = None
    ) -> None:
        if not PREFIX_PATTERN.match(prefix):
            raise ValueError(
                f"DisplayIDType prefix must be 1-16 lowercase letters, got: {prefix!r}"
            )
        registry._register_type_prefix(prefix)
        self.prefix = prefix
        self.regex = rf"{prefix}_{ENCODED_UUID_REGEX}"
        self._factory = factory

    def __repr__(self) -> str:
        return f"DisplayIDType({self.prefix!r})"

    def generate(self) -> str:
        """Return a new display ID.

        Raises:
            ImproperlyConfigured: On Python before 3.14 with no ``factory``.
        """
        factory = self._factory or getattr(uuid, "uuid7", None)
        if factory is None:
            raise ImproperlyConfigured(
                f"{self!r} needs Python 3.14+ for uuid.uuid7, or a factory: "
                f"DisplayIDType({self.prefix!r}, factory=uuid6.uuid7)"
            )
        return self.encode(factory())

    def encode(self, value: uuid.UUID | str) -> str:
        """Return the display ID for a UUID, or a hyphenated UUID string."""
        return encode_display_id(self.prefix, value)

    def parse(self, value: str) -> uuid.UUID:
        """Return the UUID in a display ID with this prefix.

        Surrounding whitespace is ignored.

        Raises:
            InvalidIdentifierError: If the value isn't a display ID.
            UnknownPrefixError: If it has another prefix.
            TypeError: If the value isn't a string.
        """
        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value).__name__}")
        result = parse_identifier(value, ("display_id",), expected_prefix=self.prefix)
        assert result.uuid is not None  # display IDs always hold one
        return result.uuid

    def is_valid(self, value: object) -> bool:
        """True if *value* is a display ID with this prefix."""
        if not isinstance(value, str):
            return False
        try:
            self.parse(value)
        except DisplayIDLookupError:
            return False
        return True
