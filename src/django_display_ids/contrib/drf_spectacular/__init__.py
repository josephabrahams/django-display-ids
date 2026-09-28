"""drf-spectacular integration for django-display-ids.

This module provides:
- OpenAPI schema extension for DisplayIDField (auto-registers when imported)
- Helper functions for documenting URL path parameters
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django_display_ids.conf import get_setting

# OpenAPI parameter description helpers
# These work regardless of whether drf-spectacular is installed


def id_param_description(
    prefix: str, *, with_uuid: bool | None = None, with_slug: bool | None = None
) -> str:
    """Generate ID parameter description with the actual prefix.

    Args:
        prefix: The display_id prefix (e.g., "user", "app").
        with_uuid: Include UUID as an identifier option. Defaults to whether
            ``"uuid"`` is in the ``DISPLAY_IDS["STRATEGIES"]`` setting.
        with_slug: Include slug as an identifier option. Defaults to whether
            ``"slug"`` is in the ``DISPLAY_IDS["STRATEGIES"]`` setting.

    Returns:
        Description string for OpenAPI parameter.

    Example:
        With the default strategies, ("display_id", "uuid", "slug"):

        >>> id_param_description("inv")
        'Identifier: display_id (inv_xxx), UUID, or slug'

        >>> id_param_description("inv", with_slug=False)
        'Identifier: display_id (inv_xxx) or UUID'

        >>> id_param_description("inv", with_uuid=False, with_slug=False)
        'Identifier: display_id (inv_xxx)'
    """
    strategies = get_setting("STRATEGIES")
    if with_uuid is None:
        with_uuid = "uuid" in strategies
    if with_slug is None:
        with_slug = "slug" in strategies

    parts = [f"display_id ({prefix}_xxx)"]
    if with_uuid:
        parts.append("UUID")
    if with_slug:
        parts.append("slug")

    if len(parts) == 1:
        return f"Identifier: {parts[0]}"
    elif len(parts) == 2:
        return f"Identifier: {parts[0]} or {parts[1]}"
    else:
        return f"Identifier: {', '.join(parts[:-1])}, or {parts[-1]}"


__all__ = [
    "id_param_description",
]

try:
    from drf_spectacular.extensions import OpenApiSerializerFieldExtension
except ImportError:
    # drf-spectacular not installed, skip extension registration
    pass
else:
    if TYPE_CHECKING:
        from drf_spectacular.openapi import AutoSchema

    from drf_spectacular.plumbing import follow_field_source
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
                prefix,
                id_param_description(
                    prefix,
                    with_uuid="uuid" in lookup.strategies,
                    with_slug="slug" in lookup.strategies,
                ),
            )
            # Keep the pattern only when display IDs are the only accepted form;
            # otherwise it would reject valid UUIDs and slugs.
            if lookup.strategies != ("display_id",):
                del schema["pattern"]
            return schema
