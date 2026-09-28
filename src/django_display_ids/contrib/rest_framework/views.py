"""Django REST Framework view mixins for identifier lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import Http404
from rest_framework.generics import get_object_or_404

from django_display_ids.exceptions import DisplayIDLookupError
from django_display_ids.resolver import _LookupOptions

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "DisplayIDMixin",
]


class DisplayIDMixin(_LookupOptions):
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

            def get_queryset(self):
                return Invoice.objects.all()  # prefix inherited from model

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

    # These may be provided by parent classes
    kwargs: dict[str, Any]
    request: Any

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

        Matches DRF's ``GenericAPIView.get_object()``: the queryset goes
        through ``filter_queryset()``, bad or unknown identifiers return 404,
        and object permissions are checked.

        Raises:
            Http404: If the identifier is invalid, has the wrong prefix, or
                matches no object. DRF turns this into a 404 response.
            AssertionError: If the URL has no ``lookup_url_kwarg`` parameter.
            MultipleObjectsReturned: If a slug matches more than one object.
        """
        queryset = self.get_queryset()
        if hasattr(self, "filter_queryset"):
            queryset = self.filter_queryset(queryset)

        # Get the identifier from URL kwargs
        value = self.kwargs.get(self.lookup_url_kwarg)
        if value is None:
            raise AssertionError(
                f"Expected view {self.__class__.__name__} to be called with a "
                f"URL keyword argument named {self.lookup_url_kwarg!r}. Fix "
                "your URL conf, or set the `.lookup_url_kwarg` attribute on "
                "the view correctly."
            )

        # Outside the try: a misconfigured lookup is an error, not a 404
        lookup = self._get_lookup(queryset.model)
        try:
            kwargs = lookup.build(str(value))
        except DisplayIDLookupError as e:
            raise Http404(str(e)) from e

        # DRF's own 404 handling; MultipleObjectsReturned propagates
        obj = get_object_or_404(queryset, **kwargs)
        self.check_object_permissions(self.request, obj)
        return obj  # type: ignore[no-any-return]
