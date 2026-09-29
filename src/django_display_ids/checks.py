"""System checks for configuration that would otherwise fail on a request.

They run with ``manage.py check`` through ``DisplayIDModel.check()`` and
``DisplayIDAdminSearchMixin.check()``, so the app doesn't need to be in
``INSTALLED_APPS``. All are warnings for now, so upgrading doesn't break a
deploy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from django.db.models.constants import LOOKUP_SEP

from .conf import get_setting
from .resolver import _resolve_slug_field, _resolve_uuid_field

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.db.models import Field

__all__: list[str] = []


def _final_field(model: type[models.Model], path: str) -> Field[Any, Any] | None:
    """The field a lookup path compares against, or None if it doesn't resolve.

    A path that ends at a relation compares against the related key, so
    ``customer`` and ``customer_id`` resolve to Customer's primary key. A
    relation without one column to compare, like a GenericForeignKey,
    doesn't resolve.
    """
    field: Any = None
    current: type[models.Model] | None = model
    for name in path.split(LOOKUP_SEP):
        if current is None:
            return None
        try:
            field = current._meta.get_field(name)
        except FieldDoesNotExist:
            return None
        current = field.related_model
    while field.is_relation:
        if field.many_to_one or (field.one_to_one and field.concrete):
            field = getattr(field, "target_field", None)
            if field is None:
                return None
        else:
            field = field.related_model._meta.pk
    return field  # type: ignore[no-any-return]


def _is_uuid_field(model: type[models.Model], path: str) -> bool:
    return isinstance(_final_field(model, path), models.UUIDField)


def _is_own_uuid_field(model: type[models.Model], name: str) -> bool:
    """True if *name* is a UUIDField on the model itself.

    Unlike ``_is_uuid_field()``, a relation doesn't count: ``display_id``
    reads the attribute, and a foreign key's attribute is an object.
    """
    try:
        return isinstance(model._meta.get_field(name), models.UUIDField)
    except FieldDoesNotExist:
        return False


def _is_unique(model: type[models.Model], name: str) -> bool:
    """True if the field is unique on its own or as part of a constraint.

    A constraint shared with other fields (unique per tenant) or with a
    condition (unique among rows that aren't deleted) counts, since lookups
    usually run on a queryset already scoped the same way.
    """
    opts = model._meta
    if getattr(opts.get_field(name), "unique", False):
        return True
    if any(name in fields for fields in opts.unique_together):
        return True
    return any(
        isinstance(c, models.UniqueConstraint) and name in c.fields
        for c in opts.constraints
    )


def check_model(model: type[models.Model]) -> list[checks.CheckMessage]:
    errors: list[checks.CheckMessage] = []

    uuid_field = _resolve_uuid_field(model, None)
    if getattr(model, "display_id_prefix", None) and not _is_own_uuid_field(
        model, uuid_field
    ):
        errors.append(
            checks.Warning(
                f"{model.__name__} has a display_id_prefix, but its uuid_field "
                f"{uuid_field!r} is not a UUIDField.",
                hint="Set uuid_field on the model to the name of its UUIDField.",
                obj=model,
                id="display_ids.W001",
            )
        )

    slug_field = _resolve_slug_field(model, None)
    try:
        model._meta.get_field(slug_field)
    except FieldDoesNotExist:
        pass
    else:
        if "slug" in get_setting("STRATEGIES") and not _is_unique(model, slug_field):
            errors.append(
                checks.Warning(
                    f"{model.__name__}.{slug_field} is not unique, so a slug "
                    "lookup raises MultipleObjectsReturned if two rows share it.",
                    hint=(
                        "Make the field unique, add a UniqueConstraint that "
                        "includes it, or remove 'slug' from "
                        'DISPLAY_IDS["STRATEGIES"].'
                    ),
                    obj=model,
                    id="display_ids.W002",
                )
            )
    return errors


def check_admin(admin: Any) -> list[checks.CheckMessage]:
    model_admin: ModelAdmin[Any] = admin
    model = model_admin.model
    obj = type(model_admin)

    try:
        lookup = admin._get_lookup(model)
    except (ImproperlyConfigured, ValueError) as e:
        return [checks.Warning(str(e), obj=obj, id="display_ids.W005")]

    errors: list[checks.CheckMessage] = []
    uses_uuid = {"uuid", "display_id"} & set(lookup.strategies)
    if uses_uuid and not _is_own_uuid_field(model, lookup.uuid_field):
        errors.append(
            checks.Warning(
                f"{obj.__name__} searches {model.__name__}.{lookup.uuid_field} "
                "by UUID, but it is not a UUIDField.",
                hint=(
                    "Set uuid_field on the admin or the model to the name of "
                    "its UUIDField, or remove DisplayIDAdminSearchMixin."
                ),
                obj=obj,
                id="display_ids.W003",
            )
        )

    for path in admin.display_id_search_fields:
        if not _is_uuid_field(model, path):
            errors.append(
                checks.Warning(
                    f"display_id_search_fields key {path!r} on {obj.__name__} "
                    f"does not end at a UUIDField of {model.__name__}.",
                    hint=(
                        "Use a lookup path to a UUIDField, such as "
                        "'customer__uid' when the UUID isn't Customer's "
                        "primary key."
                    ),
                    obj=obj,
                    id="display_ids.W004",
                )
            )
    return errors
