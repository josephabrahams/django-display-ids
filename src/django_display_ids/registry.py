"""Which prefixes are taken, by models and by DisplayIDType.

Kept apart from ``models.py`` so DisplayIDType can check it without defining
a model, which would need the app registry to be ready. Read these through
the module (``registry._prefix_registry``) so tests can swap them out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db import models

# Registry of prefix -> model class (for collision detection)
_prefix_registry: dict[str, type[models.Model]] = {}

# Prefixes taken by DisplayIDType, so a model can't reuse one
_type_prefixes: set[str] = set()


def _dotted_path(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def _register_prefix(prefix: str, cls: type[models.Model]) -> None:
    """Register a prefix for a model, checking for collisions.

    Models are compared by module and class name, not identity, so a module
    that gets imported twice (as Django's test runner can do) re-registers
    cleanly, while two different models with the same class name still
    collide.

    Raises:
        ValueError: If prefix is already registered to a different model,
            or used by a DisplayIDType.
    """
    if prefix in _type_prefixes:
        raise ValueError(
            f"Display ID prefix '{prefix}' is already used by a DisplayIDType, "
            f"cannot reuse for {_dotted_path(cls)}"
        )
    existing = _prefix_registry.get(prefix)
    if existing is not None and _dotted_path(existing) != _dotted_path(cls):
        raise ValueError(
            f"Display ID prefix '{prefix}' is already used by "
            f"{_dotted_path(existing)}, cannot reuse for {_dotted_path(cls)}"
        )
    _prefix_registry[prefix] = cls


def _register_type_prefix(prefix: str) -> None:
    """Register a DisplayIDType's prefix.

    Types can share a prefix with each other, since a module that's imported
    twice makes a second, identical type. Only a model's prefix clashes.

    Raises:
        ValueError: If a model already uses the prefix.
    """
    if prefix in _prefix_registry:
        raise ValueError(
            f"Display ID prefix '{prefix}' is already used by "
            f"{_dotted_path(_prefix_registry[prefix])}"
        )
    _type_prefixes.add(prefix)
