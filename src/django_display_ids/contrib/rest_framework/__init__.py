"""Django REST Framework integration for django-display-ids."""

# Registers the drf-spectacular schema extensions. Does nothing when
# drf-spectacular isn't installed.
from django_display_ids.contrib import drf_spectacular as _drf_spectacular  # noqa: F401

from .serializers import DisplayIDField, DisplayIDRelatedField
from .views import DisplayIDMixin

__all__ = [
    "DisplayIDField",
    "DisplayIDMixin",
    "DisplayIDRelatedField",
]
