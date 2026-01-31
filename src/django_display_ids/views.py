"""Django view mixins for identifier lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import Http404

from .conf import get_setting
from .encoding import PREFIX_PATTERN
from .exceptions import (
    InvalidIdentifierError,
    LookupError,
    ObjectNotFoundError,
    UnknownPrefixError,
)
from .resolver import resolve_object
from .typing import StrategyName  # noqa: TC001 - used at runtime in type hints

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "DisplayIDObjectMixin",
]

_NOT_SET: Any = object()


class DisplayIDObjectMixin:
    """Mixin for Django CBVs that resolves objects by display ID, UUID, or slug.

    Drop-in replacement for SingleObjectMixin's get_object() method.
    Works with DetailView, UpdateView, DeleteView, etc.

    Attributes:
        model: The model class to query.
        lookup_param: URL parameter name containing the identifier.
        lookup_strategies: Tuple of strategy names to try in order.
        display_id_prefix: Expected prefix for display IDs (optional).
        uuid_field: Name of the UUID field on the model.
        slug_field: Name of the slug field on the model.

    Example:
        class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
            model = Invoice
            lookup_param = "id"
            lookup_strategies = ("display_id", "uuid")
            display_id_prefix = "inv"
    """

    model: type[models.Model] | None = None
    lookup_param: str = "pk"
    lookup_strategies: tuple[StrategyName, ...] | None = None
    display_id_prefix: str | None = _NOT_SET
    uuid_field: str | None = None
    slug_field: str | None = None

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

    def _get_display_id_prefix(self) -> str | None:
        """Get the display ID prefix.

        Returns the view's display_id_prefix if set (including None to
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
        if self.model is not None:
            return getattr(self.model, "display_id_prefix", None)
        return None

    # These may be provided by parent classes
    kwargs: dict[str, Any]

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
            Http404: If the object is not found or identifier is invalid.
        """
        if self.model is None:
            raise AttributeError(f"{self.__class__.__name__} must define 'model'")

        # Get the identifier from URL kwargs
        value = self.kwargs.get(self.lookup_param)
        if value is None:
            raise Http404(f"Missing URL parameter: {self.lookup_param}")

        # Use provided queryset or get from get_queryset()
        qs = queryset if queryset is not None else self.get_queryset()

        try:
            return resolve_object(  # type: ignore[no-any-return]
                model=self.model,
                value=str(value),
                strategies=self._get_strategies(),
                prefix=self._get_display_id_prefix(),
                uuid_field=self._get_uuid_field(),
                slug_field=self._get_slug_field(),
                queryset=qs,
            )
        except ObjectNotFoundError as e:
            raise Http404(str(e)) from e
        except (InvalidIdentifierError, UnknownPrefixError) as e:
            raise Http404(str(e)) from e
        except LookupError as e:
            raise Http404(str(e)) from e
