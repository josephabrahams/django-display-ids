"""drf-spectacular extension for DisplayIDField.

This extension auto-registers when drf-spectacular is installed, providing
proper OpenAPI schema generation for DisplayIDField.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from drf_spectacular.extensions import OpenApiSerializerFieldExtension
except ImportError:
    # drf-spectacular not installed, skip extension registration
    pass
else:
    if TYPE_CHECKING:
        from drf_spectacular.openapi import AutoSchema

    from django_display_ids.encoding import ENCODED_UUID_LENGTH, encode_uuid
    from django_display_ids.examples import example_uuid_for_prefix

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
                example_uuid = example_uuid_for_prefix(prefix)
                example_encoded = encode_uuid(example_uuid)
                example = f"{prefix}_{example_encoded}"
                description = f"Human-readable identifier with '{prefix}_' prefix"
            else:
                example_uuid = example_uuid_for_prefix("type")
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
