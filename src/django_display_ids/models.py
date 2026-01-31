"""Model mixin for display ID support."""

from __future__ import annotations

from typing import Any, ClassVar

from django.db import models

from .conf import get_setting
from .encoding import PREFIX_PATTERN, encode_display_id

__all__ = [
    "DisplayIDMixin",
    "get_model_for_prefix",
]

# Registry of prefix -> model class name (for collision detection)
_prefix_registry: dict[str, str] = {}


def get_model_for_prefix(prefix: str) -> str | None:
    """Get the model name registered for a prefix.

    Args:
        prefix: The display ID prefix.

    Returns:
        Model class name or None if not registered.
    """
    return _prefix_registry.get(prefix)


def _register_prefix(prefix: str, model_name: str) -> None:
    """Register a prefix for a model, checking for collisions.

    Args:
        prefix: The display ID prefix.
        model_name: The model class name.

    Raises:
        ValueError: If prefix is already registered to a different model.
    """
    if prefix in _prefix_registry:
        existing = _prefix_registry[prefix]
        if existing != model_name:
            raise ValueError(
                f"Display ID prefix '{prefix}' is already used by "
                f"{existing}, cannot reuse for {model_name}"
            )
    _prefix_registry[prefix] = model_name


class DisplayIDMixin(models.Model):
    """Mixin that adds display_id support to a Django model.

    Subclasses must define `display_id_prefix` as a class attribute.
    Optionally override `uuid_field` or `slug_field` if using non-default field names.

    Example:
        class Invoice(DisplayIDMixin):
            display_id_prefix = "inv"

            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            # ...

        invoice = Invoice.objects.first()
        invoice.display_id  # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

    Example with custom field names:
        class Product(DisplayIDMixin):
            display_id_prefix = "prod"
            uuid_field = "uid"
            slug_field = "handle"

            uid = models.UUIDField(default=uuid.uuid4, unique=True)
            handle = models.SlugField(unique=True)
            # ...
    """

    display_id_prefix: ClassVar[str | None] = None
    uuid_field: ClassVar[str | None] = None
    slug_field: ClassVar[str | None] = None

    class Meta:
        abstract = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Register prefix when subclass is created."""
        super().__init_subclass__(**kwargs)

        # Only register if THIS class defines the prefix (not inherited)
        if "display_id_prefix" in cls.__dict__:
            prefix = cls.__dict__["display_id_prefix"]
            if prefix is not None:
                if not PREFIX_PATTERN.match(prefix):
                    raise ValueError(
                        f"{cls.__name__}.display_id_prefix must be 1-16 "
                        f"lowercase letters, got: {prefix!r}"
                    )
                _register_prefix(prefix, cls.__name__)

    @classmethod
    def _get_uuid_field(cls) -> str:
        if cls.uuid_field is not None:
            return cls.uuid_field
        return str(get_setting("UUID_FIELD"))

    @classmethod
    def _get_slug_field(cls) -> str:
        if cls.slug_field is not None:
            return cls.slug_field
        return str(get_setting("SLUG_FIELD"))

    @classmethod
    def get_display_id_prefix(cls) -> str | None:
        """Get the display ID prefix for this model.

        Returns:
            The prefix string, or None if not defined.
        """
        return getattr(cls, "display_id_prefix", None)

    @property
    def display_id(self) -> str | None:
        """Generate the display ID for this instance.

        Returns:
            Display ID in format {prefix}_{base62(uuid)}, or None if no prefix
            or if the UUID field is None (e.g., unsaved instance).
        """
        prefix = self.get_display_id_prefix()
        if prefix is None:
            return None
        uuid_value = getattr(self, self._get_uuid_field())
        if uuid_value is None:
            return None
        return encode_display_id(prefix, uuid_value)

    # Django admin display configuration
    display_id.fget.short_description = "Display ID"  # type: ignore[attr-defined]
