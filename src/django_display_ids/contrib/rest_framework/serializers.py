"""Django REST Framework serializer fields for display IDs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.relations import (
    MANY_RELATION_KWARGS,
    ManyRelatedField,
    PKOnlyObject,
    SlugRelatedField,
)

from django_display_ids.conf import get_setting
from django_display_ids.encoding import PREFIX_PATTERN, encode_display_id
from django_display_ids.exceptions import DisplayIDLookupError
from django_display_ids.resolver import _Lookup, _LookupOptions

if TYPE_CHECKING:
    from django.db import models

    from django_display_ids.typing import StrategyName

__all__ = [
    "DisplayIDField",
    "DisplayIDRelatedField",
]


class DisplayIDField(serializers.SerializerMethodField):
    """Serializer field that returns the display_id from a model.

    Automatically generates OpenAPI schema with the correct prefix example
    when drf-spectacular is installed.

    By default the field reads `display_id_prefix` from the serialized
    instance to determine the prefix. If the instance has no prefix, the
    field raises ValueError unless ``required=False`` is passed.

    Example:
        class InvoiceSerializer(serializers.ModelSerializer):
            display_id = DisplayIDField()

        # Output: {"id": "...", "display_id": "inv_2aUyqjCzEIiEcYMKj7TZtw"}

    Example with custom prefix (overrides model's prefix):
        class InvoiceSerializer(serializers.ModelSerializer):
            display_id = DisplayIDField(prefix="bill")

    Example deriving the prefix from a referenced model class. Use this when
    the serialized row is a *projection* of another model (e.g. a
    database-view-backed report row) that mirrors that model's data but is
    not an instance of it and carries no ``display_id_prefix`` of its own:

        class InvoiceReportSerializer(serializers.ModelSerializer):
            # InvoiceReport is a view-backed projection of Invoice.
            display_id = DisplayIDField(prefix_from=Invoice)

    Example tolerating instances without a prefix (returns None instead of
    raising). Use this when a single serializer handles heterogeneous rows,
    only some of which carry a prefix:

        class FeedItemSerializer(serializers.ModelSerializer):
            display_id = DisplayIDField(required=False)

    Attributes:
        prefix: Optional prefix override. If not set, uses prefix_from or
            the instance's display_id_prefix attribute.
    """

    def __init__(
        self,
        prefix: str | None = None,
        prefix_from: type[models.Model] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the field.

        Args:
            prefix: Optional prefix override. Mutually exclusive with
                prefix_from.
            prefix_from: Optional model class to read display_id_prefix from.
                Use this when the serialized row is a projection of another
                model and does not carry display_id_prefix itself. Mutually
                exclusive with prefix.
            **kwargs: Additional arguments passed to SerializerMethodField.
                Pass ``required=False`` to return None instead of raising
                when no prefix can be resolved for an instance.

        Raises:
            ValueError: If prefix is invalid, if both prefix and prefix_from
                are passed, or if prefix_from points at a class with no
                display_id_prefix attribute.
        """
        if prefix is not None and prefix_from is not None:
            raise ValueError("prefix and prefix_from are mutually exclusive.")

        if prefix is not None and not PREFIX_PATTERN.match(prefix):
            raise ValueError(f"prefix must be 1-16 lowercase letters, got: {prefix!r}")

        prefix_from_value: str | None = None
        if prefix_from is not None:
            resolved = getattr(prefix_from, "display_id_prefix", None)
            if resolved is None:
                raise ValueError(
                    f"prefix_from={prefix_from.__name__} has no "
                    f"display_id_prefix attribute."
                )
            if not PREFIX_PATTERN.match(resolved):
                raise ValueError(
                    f"prefix_from={prefix_from.__name__} has an invalid "
                    f"display_id_prefix: {resolved!r}"
                )
            prefix_from_value = resolved

        self._prefix_override = prefix
        self._prefix_from_value = prefix_from_value
        self._required = kwargs.get("required", True)
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    @property
    def _computed_prefix(self) -> str | None:
        """Prefix resolved from prefix= or prefix_from=, independent of obj."""
        if self._prefix_override is not None:
            return self._prefix_override
        return self._prefix_from_value

    def get_prefix(self, obj: models.Model) -> str | None:
        """Get the prefix for the display ID.

        Args:
            obj: The model instance.

        Returns:
            The prefix string or None if not available.
        """
        computed = self._computed_prefix
        if computed is not None:
            return computed
        return getattr(obj, "display_id_prefix", None)

    def to_representation(self, obj: models.Model) -> str | None:
        """Return the display_id from the model.

        Args:
            obj: The model instance.

        Returns:
            The display_id string, or None if no prefix is available and the
            field was created with required=False.

        Raises:
            ValueError: If no prefix is available (neither on field nor model)
                and the field is required.
        """
        prefix = self.get_prefix(obj)
        if prefix is None:
            if not self._required:
                return None
            raise ValueError(
                f"DisplayIDField requires a prefix. Either set prefix= or "
                f"prefix_from= on the field, add display_id_prefix to "
                f"{obj.__class__.__name__}, or pass required=False."
            )

        # With an explicit prefix (prefix= or prefix_from=), the serialized obj
        # may be a projection without its own display_id property, so compute
        # the display_id directly from the uuid field.
        if self._computed_prefix is not None:
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


class DisplayIDRelatedField(_LookupOptions, serializers.RelatedField):  # type: ignore[type-arg]
    """Writable related field that uses display IDs.

    Responses show the related object's display ID. Requests accept a display
    ID, a UUID, or a slug, parsed with the same rules as the view mixins, so
    a client can send back exactly what it read.

    Example:
        class InvoiceSerializer(serializers.ModelSerializer):
            customer = DisplayIDRelatedField(queryset=Customer.objects.all())
            tags = DisplayIDRelatedField(queryset=Tag.objects.all(), many=True)

        # Output: {"customer": "cust_2aUyqjCzEIiEcYMKj7TZtw", "tags": [...]}
        # Input accepts "cust_2aUy...", "550e8400-...", or a slug

    The related model needs a ``display_id_prefix``, or pass
    ``display_id_prefix=``. The other options work like the view mixins':
    ``lookup_strategies``, ``uuid_field`` and ``slug_field`` default to the
    related model's attributes, then the ``DISPLAY_IDS`` settings.
    """

    default_error_messages = {  # noqa: RUF012 - same as DRF's own fields
        # DRF's own messages, so DRF's translations apply
        "does_not_exist": SlugRelatedField.default_error_messages["does_not_exist"],
        "invalid": SlugRelatedField.default_error_messages["invalid"],
        "incorrect_type": _(
            "Incorrect type. Expected an identifier string, received {data_type}."
        ),
    }

    def __init__(
        self,
        *,
        lookup_strategies: tuple[StrategyName, ...] | None = None,
        display_id_prefix: str | None = None,
        uuid_field: str | None = None,
        slug_field: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.lookup_strategies = lookup_strategies
        self.display_id_prefix = display_id_prefix
        self.uuid_field = uuid_field
        self.slug_field = slug_field
        super().__init__(**kwargs)
        # Resolved once per model. DRF re-runs __init__ when it copies fields
        # for each serializer instance, so this never outlives a settings change.
        self._lookups: dict[type[models.Model], _Lookup] = {}
        # Fail at startup, not on the first request, when the related model
        # can't have display IDs.
        if self.queryset is not None:
            self._lookup_for(self.queryset.model).require_prefix()

    def _lookup_for(self, model: type[models.Model]) -> _Lookup:
        if model not in self._lookups:
            self._lookups[model] = self._get_lookup(model)
        return self._lookups[model]

    @classmethod
    def many_init(cls, *args: Any, **kwargs: Any) -> ManyRelatedField:
        # DRF's own many_init, with a list field that looks up in one query
        list_kwargs: dict[str, Any] = {"child_relation": cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return _ManyDisplayIDRelatedField(**list_kwargs)

    def use_pk_only_optimization(self) -> bool:
        # Like PrimaryKeyRelatedField: when the UUID field is the primary key,
        # the display ID can be built from the foreign key column alone, so
        # serializing doesn't load each related object.
        if self.queryset is None:
            return False
        model = self.queryset.model
        return model._meta.pk.name == self._lookup_for(model).uuid_field  # type: ignore[no-any-return]

    def to_internal_value(self, data: Any) -> Any:
        queryset = self.get_queryset()
        # Outside the try: a misconfigured lookup is an error, not bad input
        lookup = self._lookup_for(queryset.model)
        if not isinstance(data, str | uuid.UUID):
            self.fail("incorrect_type", data_type=type(data).__name__)
        try:
            kwargs = lookup.build(data)
        except DisplayIDLookupError:
            # What SlugRelatedField reports for a value it can't use
            self.fail("invalid")
        try:
            return queryset.get(**kwargs)
        except ObjectDoesNotExist:
            self._fail_does_not_exist(data)

    def _fail_does_not_exist(self, value: Any) -> None:
        self.fail("does_not_exist", slug_name="identifier", value=smart_str(value))

    def _to_internal_values(self, data: list[Any]) -> list[Any]:
        """``to_internal_value()`` for a list, in one query."""
        queryset = self.get_queryset()
        lookup = self._lookup_for(queryset.model)
        for item in data:
            if not isinstance(item, str | uuid.UUID):
                self.fail("incorrect_type", data_type=type(item).__name__)
            try:
                lookup.build(item)
            except DisplayIDLookupError:
                self.fail("invalid")
        found = lookup.fetch_many(queryset, data)
        for item in data:
            if found[item] is None:
                self._fail_does_not_exist(item)
        return [found[item] for item in data]

    def to_representation(self, value: Any) -> str:
        if isinstance(value, PKOnlyObject):
            # Only used when there's a queryset; see use_pk_only_optimization
            return self._lookup_for(self.queryset.model).encode(value.pk)  # type: ignore[union-attr]
        lookup = self._lookup_for(type(value))
        return lookup.encode(getattr(value, lookup.uuid_field))


class _ManyDisplayIDRelatedField(ManyRelatedField):
    """``many=True`` list that looks up every item in one query.

    DRF's ``ManyRelatedField`` runs one query per item.
    """

    child_relation: DisplayIDRelatedField

    def to_internal_value(self, data: Any) -> list[Any]:
        # The same checks as ManyRelatedField.to_internal_value()
        if isinstance(data, str) or not hasattr(data, "__iter__"):
            self.fail("not_a_list", input_type=type(data).__name__)
        data = list(data)
        if not self.allow_empty and len(data) == 0:
            self.fail("empty")
        return self.child_relation._to_internal_values(data)
