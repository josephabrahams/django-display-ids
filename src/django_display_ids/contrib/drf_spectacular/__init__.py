"""drf-spectacular integration for django-display-ids.

This module provides:
- OpenAPI schema extension for DisplayIDField (auto-registers when imported)
- Helper functions for documenting URL path parameters
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# OpenAPI parameter description helpers
# These work regardless of whether drf-spectacular is installed


def id_param_description(
    prefix: str, *, with_uuid: bool = True, with_slug: bool = False
) -> str:
    """Generate ID parameter description with the actual prefix.

    Args:
        prefix: The display_id prefix (e.g., "user", "app").
        with_uuid: Include UUID as an identifier option.
        with_slug: Include slug as an identifier option.

    Returns:
        Description string for OpenAPI parameter.

    Example:
        >>> id_param_description("user")
        'Identifier: display_id (user_xxx) or UUID'

        >>> id_param_description("user", with_uuid=False)
        'Identifier: display_id (user_xxx)'

        >>> id_param_description("app", with_slug=True)
        'Identifier: display_id (app_xxx), UUID, or slug'

        >>> id_param_description("app", with_uuid=False, with_slug=True)
        'Identifier: display_id (app_xxx) or slug'
    """
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

    from django_display_ids.encoding import ENCODED_UUID_LENGTH, encode_uuid
    from django_display_ids.examples import example_uuid as make_example_uuid

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
            # Get prefix from field override or try to get from model
            prefix = self.target._prefix_override

            if prefix is None:
                parent = self.target.parent
                if parent is not None:
                    # Try serializer's display_id_prefix attribute first
                    prefix = getattr(parent, "display_id_prefix", None)

                    # Then try Meta.model.display_id_prefix
                    if prefix is None:
                        meta = getattr(parent, "Meta", None)
                        model = getattr(meta, "model", None) if meta else None
                        if model is not None:
                            prefix = getattr(model, "display_id_prefix", None)

            # Try to get prefix from view's queryset model
            if prefix is None:
                model = self._get_model_from_view(auto_schema)
                if model is not None:
                    prefix = getattr(model, "display_id_prefix", None)

            # Build schema
            if prefix:
                example_uuid = make_example_uuid(prefix)
                example_encoded = encode_uuid(example_uuid)
                example = f"{prefix}_{example_encoded}"
                description = f"Human-readable identifier with '{prefix}_' prefix"
            else:
                example_uuid = make_example_uuid("type")
                example_encoded = encode_uuid(example_uuid)
                example = f"type_{example_encoded}"
                description = "Human-readable identifier with type prefix"

            return {
                "type": "string",
                "description": description,
                "example": example,
                "pattern": f"^[a-z]{{1,16}}_[0-9A-Za-z]{{{ENCODED_UUID_LENGTH}}}$",
                "readOnly": True,
            }
