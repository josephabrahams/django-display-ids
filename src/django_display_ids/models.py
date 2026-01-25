"""Model mixin for display ID support."""

from __future__ import annotations

from typing import ClassVar

from django.db import models

from .conf import get_setting
from .encoding import encode_display_id

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


class DisplayIDMeta(models.base.ModelBase):
    """Metaclass that registers display ID prefixes and detects collisions."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict,
        **kwargs,
    ):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Skip abstract models
        if getattr(cls, "_meta", None) and getattr(cls._meta, "abstract", False):  # type: ignore[attr-defined]
            return cls

        # Check if this model defines a prefix (not inherited)
        prefix = namespace.get("display_id_prefix")
        if prefix is not None:
            if prefix in _prefix_registry:
                raise ValueError(
                    f"Display ID prefix '{prefix}' is already used by "
                    f"{_prefix_registry[prefix]}, cannot reuse for {name}"
                )
            _prefix_registry[prefix] = name

        return cls


class DisplayIDMixin(models.Model, metaclass=DisplayIDMeta):
    """Mixin that adds display_id support to a Django model.

    Subclasses must define `display_id_prefix` as a class attribute.
    Optionally override `uuid_field` or `slug_field` if using non-default field names.

    Example:
        class Invoice(DisplayIDMixin):
            display_id_prefix = "inv"

            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            # ...

        invoice = Invoice.objects.first()
        invoice.display_id  # -> "inv_1a2B3c4D5e6F7g8H9i0J1k"

    Example with custom field names:
        class Product(DisplayIDMixin):
            display_id_prefix = "prod"
            uuid_field = "uid"
            slug_field = "handle"

            uid = models.UUIDField(default=uuid.uuid4, unique=True)
            handle = models.SlugField(unique=True)
            # ...
    """

    display_id_prefix: ClassVar[str]
    uuid_field: ClassVar[str | None] = None
    slug_field: ClassVar[str | None] = None

    class Meta:
        abstract = True

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
    def get_display_id_prefix(cls) -> str:
        """Get the display ID prefix for this model.

        Returns:
            The prefix string.

        Raises:
            NotImplementedError: If display_id_prefix is not defined.
        """
        # Check if prefix is defined on this class (not just inherited as the ClassVar)
        prefix = getattr(cls, "display_id_prefix", None)
        if prefix is None:
            raise NotImplementedError(
                f"{cls.__name__} must define 'display_id_prefix' class attribute"
            )
        return prefix

    @property
    def display_id(self) -> str:
        """Generate the display ID for this instance.

        Returns:
            Display ID in format {prefix}_{base62(uuid)}.

        Raises:
            NotImplementedError: If display_id_prefix is not defined.
        """
        prefix = self.get_display_id_prefix()
        uuid_value = getattr(self, self._get_uuid_field())
        return encode_display_id(prefix, uuid_value)
