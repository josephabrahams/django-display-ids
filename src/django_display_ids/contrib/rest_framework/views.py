"""Django REST Framework view mixins for identifier lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django_display_ids.conf import get_setting
from django_display_ids.encoding import PREFIX_PATTERN
from django_display_ids.exceptions import (
    InvalidIdentifierError,
    LookupError,
    ObjectNotFoundError,
    UnknownPrefixError,
)
from django_display_ids.resolver import resolve_object
from django_display_ids.typing import StrategyName  # noqa: TC001 - used at runtime

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "DisplayIDLookupMixin",
]

_NOT_SET: Any = object()


def _get_drf_exceptions() -> tuple[type[Exception], type[Exception]]:
    """Lazily import DRF exceptions to avoid hard dependency."""
    try:
        from rest_framework.exceptions import NotFound, ParseError

        return NotFound, ParseError
    except ImportError:
        raise ImportError(
            "Django REST Framework is required for DisplayIDLookupMixin. "
            "Install it with: pip install djangorestframework"
        ) from None


class DisplayIDLookupMixin:
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
        class InvoiceView(DisplayIDLookupMixin, APIView):
            lookup_url_kwarg = "id"
            lookup_strategies = ("display_id", "uuid")
            display_id_prefix = "inv"

            def get(self, request, *args, **kwargs):
                invoice = self.get_object()
                return Response({"id": str(invoice.id)})

    Example with ViewSet:
        class InvoiceViewSet(DisplayIDLookupMixin, ModelViewSet):
            queryset = Invoice.objects.all()
            serializer_class = InvoiceSerializer
            lookup_url_kwarg = "pk"
            lookup_strategies = ("display_id", "uuid")
    """

    lookup_url_kwarg: str = "pk"
    lookup_strategies: tuple[StrategyName, ...] | None = None
    display_id_prefix: str | None = _NOT_SET
    uuid_field: str | None = None
    slug_field: str | None = None

    # These may be provided by parent classes
    kwargs: dict[str, Any]
    request: Any

    def _get_uuid_field(self) -> str:
        if self.uuid_field is not None:
            return self.uuid_field
        return str(get_setting("UUID_FIELD"))

    def _get_slug_field(self) -> str:
        if self.slug_field is not None:
            return self.slug_field
        return str(get_setting("SLUG_FIELD"))

    def _get_strategies(self) -> tuple[StrategyName, ...]:
        if self.lookup_strategies is not None:
            return self.lookup_strategies
        return get_setting("STRATEGIES")  # type: ignore[return-value]

    def _get_display_id_prefix(self, model: type[models.Model]) -> str | None:
        """Get the display ID prefix.

        Returns the viewset's display_id_prefix if set (including None to
        explicitly disable), otherwise falls back to the model's
        display_id_prefix attribute.
        """
        if self.display_id_prefix is not _NOT_SET:
            if self.display_id_prefix is not None and not PREFIX_PATTERN.match(
                self.display_id_prefix
            ):
                raise ValueError(
                    f"display_id_prefix must be 1-16 lowercase letters, "
                    f"got: {self.display_id_prefix!r}"
                )
            return self.display_id_prefix
        return getattr(model, "display_id_prefix", None)

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
                model=model,
                value=str(value),
                strategies=self._get_strategies(),
                prefix=self._get_display_id_prefix(model),
                uuid_field=self._get_uuid_field(),
                slug_field=self._get_slug_field(),
                queryset=queryset,
            )
        except ObjectNotFoundError as e:
            raise NotFound(str(e)) from e
        except (InvalidIdentifierError, UnknownPrefixError) as e:
            raise ParseError(str(e)) from e
        except LookupError as e:
            raise ParseError(str(e)) from e

        # Check object-level permissions
        self.check_object_permissions(self.request, obj)

        return obj  # type: ignore[no-any-return]
