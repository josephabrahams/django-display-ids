"""Django REST Framework serializer fields for display IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework import serializers

from django_display_ids.conf import get_setting
from django_display_ids.encoding import PREFIX_PATTERN, encode_display_id

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "DisplayIDField",
]


class DisplayIDField(serializers.SerializerMethodField):
    """Serializer field that returns the display_id from a model.

    Automatically generates OpenAPI schema with the correct prefix example
    when drf-spectacular is installed.

    The field reads `display_id_prefix` from the model to determine the prefix.
    If the model has no prefix, the field returns None and can be excluded
    from serialization.

    Example:
        class UserSerializer(serializers.Serializer):
            id = serializers.UUIDField(source="uid", read_only=True)
            display_id = DisplayIDField()

        # Output: {"id": "...", "display_id": "user_2nBm7K8xYq1pLwZj"}

    Example with custom prefix (overrides model's prefix):
        class UserSerializer(serializers.Serializer):
            display_id = DisplayIDField(prefix="usr")

    Attributes:
        prefix: Optional prefix override. If not set, uses model's
            display_id_prefix attribute.
    """

    def __init__(self, prefix: str | None = None, **kwargs: Any) -> None:
        """Initialize the field.

        Args:
            prefix: Optional prefix override. If not set, uses model's
                display_id_prefix attribute.
            **kwargs: Additional arguments passed to SerializerMethodField.

        Raises:
            ValueError: If prefix is invalid (must be 1-16 lowercase letters).
        """
        if prefix is not None and not PREFIX_PATTERN.match(prefix):
            raise ValueError(f"prefix must be 1-16 lowercase letters, got: {prefix!r}")
        self._prefix_override = prefix
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def get_prefix(self, obj: models.Model) -> str | None:
        """Get the prefix for the display ID.

        Args:
            obj: The model instance.

        Returns:
            The prefix string or None if not available.
        """
        if self._prefix_override is not None:
            return self._prefix_override
        return getattr(obj, "display_id_prefix", None)

    def to_representation(self, obj: models.Model) -> str:
        """Return the display_id from the model.

        Args:
            obj: The model instance.

        Returns:
            The display_id string.

        Raises:
            ValueError: If no prefix is available (neither on field nor model).
        """
        prefix = self.get_prefix(obj)
        if prefix is None:
            raise ValueError(
                f"DisplayIDField requires a prefix. Either set prefix= on the "
                f"field or add display_id_prefix to {obj.__class__.__name__}."
            )

        # If using prefix override, generate display_id with that prefix
        if self._prefix_override is not None:
            # Get uuid_field name from model, then fall back to settings
            uuid_field_name: str | None = getattr(obj, "uuid_field", None)
            if uuid_field_name is None:
                uuid_field_name = str(get_setting("UUID_FIELD"))
            uuid_value = getattr(obj, uuid_field_name, None)
            if uuid_value is None:
                raise ValueError(
                    f"Cannot generate display_id: {obj.__class__.__name__} "
                    f"has no '{uuid_field_name}' field."
                )
            return encode_display_id(prefix, uuid_value)

        # Use the model's display_id property
        if hasattr(obj, "display_id"):
            display_id: str = obj.display_id
            return display_id

        raise ValueError(
            f"Cannot generate display_id: {obj.__class__.__name__} "
            f"has no display_id property."
        )
