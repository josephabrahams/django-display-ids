"""Model mixin for display ID support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models

from . import checks, registry
from .encoding import PREFIX_PATTERN, encode_display_id
from .resolver import _resolve_uuid_field

if TYPE_CHECKING:
    from django.core.checks import CheckMessage

__all__ = [
    "DisplayIDModel",
    "get_model_for_prefix",
]


def get_model_for_prefix(prefix: str) -> str | None:
    """Get the model name registered for a prefix.

    Args:
        prefix: The display ID prefix.

    Returns:
        Model class name or None if not registered.
    """
    cls = registry._prefix_registry.get(prefix)
    return cls.__name__ if cls is not None else None


class DisplayIDModel(models.Model):
    """Abstract base model that adds display_id support.

    Subclasses must define `display_id_prefix` as a class attribute.
    Optionally override `uuid_field` or `slug_field` if using non-default field names.

    Example:
        class Invoice(DisplayIDModel):
            display_id_prefix = "inv"
            uuid_field = "uuid"

            uuid = models.UUIDField(default=uuid.uuid7, unique=True)

        invoice = Invoice.objects.first()
        invoice.display_id  # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

    Example with custom slug field:
        class Product(DisplayIDModel):
            display_id_prefix = "prod"
            uuid_field = "uuid"
            slug_field = "handle"

            uuid = models.UUIDField(default=uuid.uuid7, unique=True)
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
                registry._register_prefix(prefix, cls)

    @classmethod
    def check(cls, **kwargs: Any) -> list[CheckMessage]:
        """Add this library's checks to the model's (see ``checks.py``)."""
        return [*super().check(**kwargs), *checks.check_model(cls)]

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
        uuid_value = getattr(self, _resolve_uuid_field(type(self), None))
        if uuid_value is None:
            return None
        return encode_display_id(prefix, uuid_value)

    # Django admin display configuration
    display_id.fget.short_description = "Display ID"  # type: ignore[attr-defined]
