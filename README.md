# django-display-ids

[![PyPI](https://img.shields.io/pypi/v/django-display-ids)](https://pypi.org/project/django-display-ids/)
[![Python](https://img.shields.io/pypi/pyversions/django-display-ids)](https://pypi.org/project/django-display-ids/)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0%20%7C%206.1-blue)](https://pypi.org/project/django-display-ids/)
[![CI](https://github.com/josephabrahams/django-display-ids/actions/workflows/ci.yml/badge.svg)](https://github.com/josephabrahams/django-display-ids/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/josephabrahams/django-display-ids/graph/badge.svg)](https://codecov.io/gh/josephabrahams/django-display-ids)
[![Docs](https://readthedocs.org/projects/django-display-ids/badge/?version=stable)](https://django-display-ids.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/josephabrahams/django-display-ids/blob/main/LICENSE)

Stripe-style prefixed IDs for Django, like `inv_2aUyqjCzEIiEcYMKj7TZtw`, on top of the UUID fields you already have. No new fields and no migrations.

```python
from django_display_ids import DisplayIDMixin, DisplayIDModel

class Invoice(DisplayIDModel):
    display_id_prefix = "inv"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    slug = models.SlugField(unique=True)

invoice.display_id  # "inv_2aUyqjCzEIiEcYMKj7TZtw"

class InvoiceDetailView(DisplayIDMixin, DetailView):
    model = Invoice
```

The view now finds the invoice from the display ID, the UUID (`550e8400-e29b-41d4-a716-446655440000`, in any case, with or without hyphens) or the slug. Each one becomes a plain query on the UUID or slug column.

A UUID in a URL or log doesn't say what it points to; a display ID does. The part after the prefix is the same UUID in base62, so it converts back without a database lookup.

## Installation

```bash
pip install django-display-ids
pip install "django-display-ids[drf]"          # with Django REST Framework
pip install "django-display-ids[spectacular]"  # with DRF and drf-spectacular
```

Requires Python 3.12+ and Django 4.2+.

## What's included

- `DisplayIDModel` for the `display_id` property, and a manager with `get_by_identifier()`, `get_by_identifiers()` and `resolve_identifier()`
- `DisplayIDMixin` for Django class-based views and for DRF views
- `DisplayIDField` and `DisplayIDRelatedField` for DRF serializers, so APIs can both show and accept display IDs, with drf-spectacular schemas
- `DisplayIDAdminSearchMixin` to search the admin by display ID, UUID or slug
- URL converters, and a `display_id` template filter for any UUID

## Documentation

[django-display-ids.readthedocs.io](https://django-display-ids.readthedocs.io/)

## Contributing

See [CONTRIBUTING.md](https://github.com/josephabrahams/django-display-ids/blob/main/CONTRIBUTING.md).

## Related projects

These generate and store prefixed IDs in a new model field, where django-display-ids works with the UUID fields you already have:

- [django-prefix-id](https://github.com/jaddison/django-prefix-id): a `PrefixIDField` that stores base62-encoded UUIDs
- [django-spicy-id](https://github.com/mik3y/django-spicy-id): a drop-in `AutoField` replacement
- [django-charid-field](https://github.com/yunojuno/django-charid-field): a `CharField` for cuid, ksuid or ulid values
