"""Django view mixins for identifier lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import Http404
from django.utils.translation import gettext as _

from .exceptions import DisplayIDLookupError
from .resolver import _LookupOptions

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "DisplayIDMixin",
]


class DisplayIDMixin(_LookupOptions):
    """Mixin for Django CBVs that resolves objects by display ID, UUID, or slug.

    Drop-in replacement for SingleObjectMixin's get_object() method.
    Works with DetailView, UpdateView, DeleteView, etc.

    Attributes:
        model: The model class to query.
        lookup_url_kwarg: URL parameter name containing the identifier.
        lookup_strategies: Tuple of strategy names to try in order.
        display_id_prefix: Expected prefix for display IDs (optional).
        uuid_field: Name of the UUID field on the model.
        slug_field: Name of the slug field on the model.

    Example:
        class InvoiceDetailView(DisplayIDMixin, DetailView):
            model = Invoice  # prefix inherited from model
            lookup_url_kwarg = "id"
    """

    model: type[models.Model] | None = None
    lookup_url_kwarg: str = "pk"

    # These may be provided by parent classes
    kwargs: dict[str, Any]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Renamed in 0.8. Without this check the old attribute would be
        # ignored and every request would fail looking for a "pk" parameter.
        if "lookup_param" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} sets lookup_param, which was renamed to "
                "lookup_url_kwarg in django-display-ids 0.8. Rename the attribute."
            )

    def get_queryset(self) -> Any:
        """Get the base queryset.

        Override this method in your view to filter the queryset.
        Falls back to model._default_manager.all() if not overridden.
        """
        if hasattr(super(), "get_queryset"):
            return super().get_queryset()  # type: ignore[misc]
        if self.model is not None:
            return self.model._default_manager.all()
        raise AttributeError(
            f"{self.__class__.__name__} must define 'model' or "
            "override 'get_queryset()'"
        )

    def get_object(self, queryset: Any | None = None) -> models.Model:
        """Retrieve the object by identifier.

        Args:
            queryset: Optional queryset to search within.

        Returns:
            The matching model instance.

        Raises:
            Http404: If the identifier is invalid, has the wrong prefix, or
                matches no object.
            AttributeError: If the URL has no ``lookup_url_kwarg`` parameter.
            MultipleObjectsReturned: If a slug matches more than one object.
        """
        # Get the identifier from URL kwargs
        value = self.kwargs.get(self.lookup_url_kwarg)
        if value is None:
            raise AttributeError(
                f"{self.__class__.__name__} must be called with a "
                f"{self.lookup_url_kwarg!r} URL parameter."
            )

        # Use provided queryset or get from get_queryset()
        qs = queryset if queryset is not None else self.get_queryset()

        # DetailView's 404 message. It's Django's own string, so Django's
        # translations apply.
        not_found = Http404(
            _("No %(verbose_name)s found matching the query")
            % {"verbose_name": qs.model._meta.verbose_name}
        )

        # Outside the try: a misconfigured lookup is an error, not a 404
        lookup = self._get_lookup(qs.model)
        try:
            kwargs = lookup.build(str(value))
        except DisplayIDLookupError:
            raise not_found from None

        # MultipleObjectsReturned propagates, as in DetailView
        try:
            return qs.get(**kwargs)  # type: ignore[no-any-return]
        except qs.model.DoesNotExist:
            raise not_found from None
