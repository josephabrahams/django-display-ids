"""drf-spectacular integration for django-display-ids.

Importing ``django_display_ids.contrib.rest_framework`` registers these
extensions when drf-spectacular is installed:

- ``DisplayIDField`` and ``DisplayIDRelatedField`` get string schemas with
  display ID examples.
- Views using ``DisplayIDMixin`` get a path parameter that describes the
  identifiers the view accepts.

``id_param_description()`` works without drf-spectacular.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django_display_ids.conf import get_setting

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django_display_ids.typing import StrategyName

# OpenAPI parameter description helpers
# These work regardless of whether drf-spectacular is installed


def id_param_description(
    prefix: str | None,
    *,
    strategies: Sequence[StrategyName] | None = None,
    with_uuid: bool | None = None,
    with_slug: bool | None = None,
) -> str:
    """Describe the identifier formats a lookup accepts.

    Args:
        prefix: The display ID prefix (e.g., "inv"). ``None`` leaves display
            IDs out, like a lookup on a model without a prefix.
        strategies: The lookup strategies to describe. Defaults to the
            ``DISPLAY_IDS["STRATEGIES"]`` setting.
        with_uuid: Include or leave out UUIDs, whatever *strategies* says.
        with_slug: Include or leave out slugs, whatever *strategies* says.

    Returns:
        Description string for an OpenAPI parameter.

    Example:
        With the default strategies, ("display_id", "uuid", "slug"):

        >>> id_param_description("inv")
        'Identifier: display_id (inv_xxx), UUID, or slug'

        >>> id_param_description("inv", strategies=("display_id", "uuid"))
        'Identifier: display_id (inv_xxx) or UUID'

        >>> id_param_description("inv", strategies=("display_id",))
        'Identifier: display_id (inv_xxx)'
    """
    if strategies is None:
        strategies = get_setting("STRATEGIES")  # type: ignore[assignment]
    assert strategies is not None
    if with_uuid is None:
        with_uuid = "uuid" in strategies
    if with_slug is None:
        with_slug = "slug" in strategies

    parts = []
    if prefix is not None and "display_id" in strategies:
        parts.append(f"display_id ({prefix}_xxx)")
    if with_uuid:
        parts.append("UUID")
    if with_slug:
        parts.append("slug")

    if len(parts) <= 1:
        return f"Identifier: {''.join(parts)}"
    elif len(parts) == 2:
        return f"Identifier: {parts[0]} or {parts[1]}"
    else:
        return f"Identifier: {', '.join(parts[:-1])}, or {parts[-1]}"


__all__ = [
    "id_param_description",
]

try:
    from drf_spectacular.extensions import (
        OpenApiSerializerFieldExtension,
        OpenApiViewExtension,
    )
except ImportError:
    # drf-spectacular not installed, skip extension registration
    pass
else:
    if TYPE_CHECKING:
        from drf_spectacular.openapi import AutoSchema

    import uritemplate
    from django.core.exceptions import ImproperlyConfigured
    from drf_spectacular.drainage import get_view_method_names, isolate_view_method
    from drf_spectacular.plumbing import follow_field_source, get_view_model
    from drf_spectacular.utils import OpenApiParameter
    from rest_framework.schemas.generators import get_pk_name
    from rest_framework.serializers import ManyRelatedField

    from django_display_ids.encoding import DISPLAY_ID_REGEX, ENCODED_UUID_REGEX
    from django_display_ids.examples import example_display_id

    def _display_id_schema(prefix: str | None, description: str) -> dict[str, Any]:
        """String schema for a display ID with *prefix*, or any prefix if None."""
        if prefix is None:
            return {
                "type": "string",
                "description": description,
                "example": example_display_id("type"),
                "pattern": f"^{DISPLAY_ID_REGEX}$",
            }
        return {
            "type": "string",
            "description": description,
            "example": example_display_id(prefix),
            "pattern": f"^{prefix}_{ENCODED_UUID_REGEX}$",
        }

    class DisplayIDFieldExtension(OpenApiSerializerFieldExtension):  # type: ignore[no-untyped-call]
        """OpenAPI schema extension for DisplayIDField.

        Generates schema with correct prefix example based on the field's
        configuration or the model's display_id_prefix.
        """

        target_class = (
            "django_display_ids.contrib.rest_framework.serializers.DisplayIDField"
        )
        match_subclasses = True

        def _get_model_from_view(self, auto_schema: AutoSchema | None) -> Any:
            """Try to get model from the view's queryset."""
            if auto_schema is None:
                return None
            view = getattr(auto_schema, "view", None)
            if view is None:
                return None
            # Try get_queryset first
            if hasattr(view, "get_queryset"):
                try:
                    queryset = view.get_queryset()
                    if hasattr(queryset, "model"):
                        return queryset.model
                except Exception:
                    pass
            # Try queryset attribute
            queryset = getattr(view, "queryset", None)
            if queryset is not None and hasattr(queryset, "model"):
                return queryset.model
            return None

        def map_serializer_field(
            self, auto_schema: AutoSchema, direction: str
        ) -> dict[str, Any]:
            """Generate OpenAPI schema for DisplayIDField."""
            # Use the same sources the field uses at runtime: prefix= or
            # prefix_from=, then the serialized model's display_id_prefix.
            prefix = self.target._computed_prefix

            if prefix is None:
                parent = self.target.parent
                meta = getattr(parent, "Meta", None) if parent is not None else None
                model = getattr(meta, "model", None) if meta else None
                if model is not None:
                    prefix = getattr(model, "display_id_prefix", None)

            # Try to get prefix from view's queryset model
            if prefix is None:
                model = self._get_model_from_view(auto_schema)
                if model is not None:
                    prefix = getattr(model, "display_id_prefix", None)

            if prefix:
                description = f"Human-readable identifier with '{prefix}_' prefix"
            else:
                description = "Human-readable identifier with type prefix"
            return {**_display_id_schema(prefix or None, description), "readOnly": True}

    class DisplayIDRelatedFieldExtension(OpenApiSerializerFieldExtension):  # type: ignore[no-untyped-call]
        """OpenAPI schema extension for DisplayIDRelatedField.

        Responses show a display ID. Requests list the identifier formats the
        field accepts, which depend on its lookup strategies. ``many=True``
        fields become arrays of this schema through drf-spectacular's own
        handling of ``ManyRelatedField``.
        """

        target_class = (
            "django_display_ids.contrib.rest_framework.serializers."
            "DisplayIDRelatedField"
        )
        match_subclasses = True

        def _related_model(self) -> Any:
            field = self.target
            if field.queryset is not None:
                return field.queryset.model
            # Read-only fields have no queryset. Find the model from the
            # serializer the same way drf-spectacular does for its own related
            # fields, including many=True and dotted sources.
            parent, source = field.parent, field.source
            if isinstance(parent, ManyRelatedField):
                parent, source = parent.parent, parent.source
            model = getattr(getattr(parent, "Meta", None), "model", None)
            if model is None:
                return None
            # For a relation this returns the target model's primary key field
            target = follow_field_source(  # type: ignore[no-untyped-call]
                model, source.split("."), emit_warnings=False
            )
            return getattr(target, "model", None)

        def map_serializer_field(
            self, auto_schema: AutoSchema, direction: str
        ) -> dict[str, Any]:
            """Generate OpenAPI schema for DisplayIDRelatedField."""
            model = self._related_model()
            if model is None:
                return {"type": "string", "example": example_display_id("type")}

            lookup = self.target._lookup_for(model)
            prefix = lookup.require_prefix()
            if direction == "response":
                return _display_id_schema(
                    prefix, f"Display ID of the related {model.__name__}"
                )
            schema = _display_id_schema(
                prefix, id_param_description(prefix, strategies=lookup.strategies)
            )
            # Keep the pattern only when display IDs are the only accepted form;
            # otherwise it would reject valid UUIDs and slugs.
            if lookup.strategies != ("display_id",):
                del schema["pattern"]
            return schema

    def _path_variable(view: Any, path: str) -> str | None:
        """The name of the view's identifier in *path*, or None if absent."""
        variables = set(uritemplate.variables(path))
        name: str = view.lookup_url_kwarg
        if name in variables:
            return name
        # Schema generation renames {pk}, the same way as DRF's coerce_path()
        if name == "pk":
            model = getattr(getattr(view, "queryset", None), "model", None)
            coerced: str = get_pk_name(model) if model is not None else "id"
            if coerced in variables:
                return coerced
        return None

    def _path_parameter(view: Any, path: str) -> OpenApiParameter | None:
        """The identifier path parameter for a ``DisplayIDMixin`` view."""
        name = _path_variable(view, path)
        if name is None:
            return None
        model = get_view_model(view, emit_warnings=False)  # type: ignore[no-untyped-call]
        if model is None:
            return None
        try:
            lookup = view._get_lookup(model)
        except (ValueError, ImproperlyConfigured):
            # A broken lookup fails at request time; keep the default schema
            return None

        prefix = lookup.prefix
        schema: dict[str, Any] = {"type": "string"}
        if lookup.strategies == ("display_id",):
            schema["pattern"] = f"^{prefix}_{ENCODED_UUID_REGEX}$"
        elif lookup.strategies == ("uuid",):
            schema["format"] = "uuid"
        if prefix is not None and "display_id" in lookup.strategies:
            schema["example"] = example_display_id(prefix)
        return OpenApiParameter(
            name,
            schema,
            OpenApiParameter.PATH,
            description=id_param_description(prefix, strategies=lookup.strategies),
        )

    class _PathParameterSchema:
        """Adds the identifier path parameter to a view's or action's schema."""

        view: Any
        path: str

        def get_override_parameters(self) -> list[Any]:
            parameter = _path_parameter(self.view, self.path)
            # Earlier entries lose to later ones, so @extend_schema wins
            own = [] if parameter is None else [parameter]
            return [*own, *super().get_override_parameters()]  # type: ignore[misc]

    def _with_path_parameter(schema: Any) -> type[Any]:
        schema_class = schema if isinstance(schema, type) else schema.__class__
        return type(schema_class.__name__, (_PathParameterSchema, schema_class), {})

    class DisplayIDMixinExtension(OpenApiViewExtension):  # type: ignore[no-untyped-call]
        """Document the identifier path parameter of ``DisplayIDMixin`` views.

        The description, pattern and example come from the lookup that
        ``get_object()`` uses, so they follow the view's ``lookup_strategies``
        and the model's prefix and slug field. A parameter set with
        ``@extend_schema`` still takes precedence.
        """

        target_class = "django_display_ids.contrib.rest_framework.views.DisplayIDMixin"
        match_subclasses = True

        def view_replacement(self) -> type[Any]:
            view = type(
                self.target.__name__,
                (self.target,),
                {"schema": _with_path_parameter(self.target.schema)()},
            )
            # An action decorated with @extend_schema brings its own schema
            # class, which drf-spectacular uses instead of the view's. Give
            # it the parameter too, on a copy so the original view is
            # unchanged, the same way @extend_schema isolates methods.
            for name in get_view_method_names(view):
                action_schema = getattr(getattr(view, name), "kwargs", {}).get("schema")
                if action_schema is not None:
                    method = isolate_view_method(view, name)  # type: ignore[no-untyped-call]
                    method.kwargs["schema"] = _with_path_parameter(action_schema)
            return view
