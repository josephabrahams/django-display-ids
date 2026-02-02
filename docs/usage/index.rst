Usage Guide
===========

This section covers how to integrate django-display-ids into your Django project.

.. toctree::
   :maxdepth: 2

   models
   views
   drf
   admin
   templatetags

Overview
--------

django-display-ids provides several integration points:

**Models**
   Add the :class:`DisplayIDModel` to give your models a ``display_id`` property.
   Use :class:`DisplayIDManager` for convenient lookup methods.

**Django Views**
   Add :class:`DisplayIDMixin` to class-based views like ``DetailView``,
   ``UpdateView``, and ``DeleteView``.

**Django REST Framework**
   Use :class:`DisplayIDMixin` (from ``contrib.rest_framework``) for ViewSets and APIViews.
   Use :class:`DisplayIDField` in serializers to include display IDs in responses.

**Django Admin**
   Add :class:`DisplayIDAdminSearchMixin` to enable searching by display ID or UUID.

**Templates**
   Use the ``display_id`` filter to encode UUIDs as display IDs.
