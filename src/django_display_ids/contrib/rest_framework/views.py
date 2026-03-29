"""Django REST Framework view mixins for identifier lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django_display_ids.conf import get_setting
from django_display_ids.exceptions import (
    DisplayIDLookupError,
    ObjectNotFoundError,
)
from django_display_ids.resolver import resolve_object
from django_display_ids.typing import StrategyName  # noqa: TC001 - used at runtime

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "DisplayIDMixin",
]


def _get_drf_exceptions() -> tuple[type[Exception], type[Exception]]:
    """Lazily import DRF exceptions to avoid hard dependency."""
    try:
        from rest_framework.exceptions import NotFound, ParseError

        return NotFound, ParseError
    except ImportError:
        raise ImportError(
            "Django REST Framework is required for DisplayIDMixin. "
            "Install it with: pip install djangorestframework"
        ) from None


class DisplayIDMixin:
    """Mixin for DRF views that resolves objects by display ID, UUID, or slug.

    Works with APIView, GenericAPIView, and ViewSets. Does not require
    serializers.

    Attributes:
        lookup_url_kwarg: URL parameter name containing the identifier.
        lookup_strategies: Tuple of strategy names to try in order.
        display_id_prefix: Expected prefix for display IDs (optional).
        uuid_field: Name of the UUID field on the model.
        slug_field: Name of the slug field on the model.

    Example:
        class InvoiceView(DisplayIDMixin, APIView):
            lookup_url_kwarg = "id"
            display_id_prefix = "inv"

            def get(self, request, *args, **kwargs):
                invoice = self.get_object()
                return Response({"id": str(invoice.id)})

    Example with ViewSet:
        class InvoiceViewSet(DisplayIDMixin, ModelViewSet):
            queryset = Invoice.objects.all()
            serializer_class = InvoiceSerializer
            lookup_url_kwarg = "pk"
    """

    lookup_url_kwarg: str = "pk"
    lookup_strategies: tuple[StrategyName, ...] | None = None
    display_id_prefix: str | None = None
    uuid_field: str | None = None
    slug_field: str | None = None

    # These may be provided by parent classes
    kwargs: dict[str, Any]
    request: Any

    def _get_strategies(self) -> tuple[StrategyName, ...]:
        if self.lookup_strategies is not None:
            return self.lookup_strategies
        return get_setting("STRATEGIES")  # type: ignore[return-value]

    def get_queryset(self) -> Any:
        """Get the base queryset.

        Override this method in your view to provide the queryset.
        """
        if hasattr(super(), "get_queryset"):
            return super().get_queryset()  # type: ignore[misc]
        raise NotImplementedError(
            f"{self.__class__.__name__} must override 'get_queryset()'"
        )

    def check_object_permissions(self, request: Any, obj: Any) -> None:
        """Check object-level permissions.

        Override this method to implement custom permission checks.
        """
        if hasattr(super(), "check_object_permissions"):
            super().check_object_permissions(request, obj)  # type: ignore[misc]

    def get_object(self) -> models.Model:
        """Retrieve the object by identifier.

        Returns:
            The matching model instance.

        Raises:
            NotFound: If the object is not found.
            ParseError: If the identifier format is invalid.
        """
        NotFound, ParseError = _get_drf_exceptions()

        # Get the queryset
        queryset = self.get_queryset()

        # Get the model from the queryset
        model = queryset.model

        # Get the identifier from URL kwargs
        value = self.kwargs.get(self.lookup_url_kwarg)
        if value is None:
            raise ParseError(f"Missing URL parameter: {self.lookup_url_kwarg}")

        try:
            obj = resolve_object(
                model,
                str(value),
                strategies=self._get_strategies(),
                prefix=self.display_id_prefix,
                uuid_field=self.uuid_field,
                slug_field=self.slug_field,
                queryset=queryset,
            )
        except ObjectNotFoundError as e:
            raise NotFound(str(e)) from e
        except DisplayIDLookupError as e:
            raise ParseError(str(e)) from e

        # Check object-level permissions
        self.check_object_permissions(self.request, obj)

        return obj  # type: ignore[no-any-return]
