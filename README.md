# django-display-ids

[![PyPI](https://img.shields.io/pypi/v/django-display-ids)](https://pypi.org/project/django-display-ids/)
[![Python](https://img.shields.io/pypi/pyversions/django-display-ids)](https://pypi.org/project/django-display-ids/)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0-blue)](https://pypi.org/project/django-display-ids/)

Stripe-like prefixed IDs for Django. Works with existing UUIDs — no schema changes.

**Documentation**: [django-display-ids.readthedocs.io](https://django-display-ids.readthedocs.io/)

## Installation

```bash
pip install django-display-ids
```

No `INSTALLED_APPS` entry required.

## Quick Start

```python
from django.views.generic import DetailView
from django_display_ids import DisplayIDObjectMixin

class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
    model = Invoice
    lookup_param = "id"
    lookup_strategies = ("display_id", "uuid")
    display_id_prefix = "inv"
```

```python
# urls.py
urlpatterns = [
    path("invoices/<str:id>/", InvoiceDetailView.as_view()),
]
```

Now your view accepts:
- `inv_2aUyqjCzEIiEcYMKj7TZtw` (display ID)
- `550e8400-e29b-41d4-a716-446655440000` (UUID)

## Features

- **Multiple identifier formats**: display ID (`prefix_base62uuid`), UUID (v4/v7), slug
- **Framework support**: Django CBVs and Django REST Framework
- **Zero model changes required**: Works with any existing UUID field
- **OpenAPI integration**: Automatic schema generation with drf-spectacular

## Development

```bash
git clone https://github.com/josephabrahams/django-display-ids.git
cd django-display-ids
uv sync
```

Run tests:

```bash
uv run pytest
```

Run tests across Python and Django versions:

```bash
uvx nox
```

Lint and format:

```bash
uvx pre-commit run --all-files
```

## Related Projects

If you need ID generation and storage (custom model fields), consider:

- **[django-prefix-id](https://github.com/jaddison/django-prefix-id)** — PrefixIDField that generates and stores base62-encoded UUIDs
- **[django-spicy-id](https://github.com/mik3y/django-spicy-id)** — Drop-in AutoField replacement
- **[django-charid-field](https://github.com/yunojuno/django-charid-field)** — CharField wrapper supporting cuid, ksuid, ulid

**django-display-ids** works with existing UUID fields and handles resolution only — no migrations required.

## License

ISC
