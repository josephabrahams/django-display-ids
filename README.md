# django-display-ids

[![PyPI](https://img.shields.io/pypi/v/django-display-ids)](https://pypi.org/project/django-display-ids/)
[![Python](https://img.shields.io/pypi/pyversions/django-display-ids)](https://pypi.org/project/django-display-ids/)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0-blue)](https://pypi.org/project/django-display-ids/)
[![CI](https://github.com/josephabrahams/django-display-ids/actions/workflows/ci.yml/badge.svg)](https://github.com/josephabrahams/django-display-ids/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/josephabrahams/django-display-ids/graph/badge.svg)](https://codecov.io/gh/josephabrahams/django-display-ids)
[![Docs](https://readthedocs.org/projects/django-display-ids/badge/?version=stable)](https://django-display-ids.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/josephabrahams/django-display-ids/blob/main/LICENSE)

Stripe-like prefixed IDs for Django. Works with existing UUIDs — no schema changes.

## Why?

UUIDv7 (native in Python 3.14+) offers excellent database performance with time-ordered indexing. But they lack context — seeing `550e8400-e29b-41d4-a716-446655440000` in a URL or log doesn't tell you what kind of object it refers to.

Display IDs like `inv_2aUyqjCzEIiEcYMKj7TZtw` are more useful: the prefix identifies the object type at a glance, and they're compact and URL-safe. But storing display IDs in the database is far less efficient than native UUIDs.

Different consumers have different needs:
- **Humans** prefer slugs (`my-invoice`) or display IDs (`inv_xxx`)
- **APIs and integrations** work well with UUIDs

This library gives you the best of both worlds: accept any format in your URLs and API endpoints, then translate to an efficient UUID lookup in the database. Store UUIDs, expose whatever format your users need.

## Installation

```bash
pip install django-display-ids
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_display_ids",
]
```

## Quick Start

**Django views:**

```python
from django.views.generic import DetailView
from django_display_ids import DisplayIDObjectMixin

class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
    model = Invoice
    lookup_param = "id"
    lookup_strategies = ("display_id", "uuid", "slug")
    display_id_prefix = "inv"
```

**Django REST Framework:**

```python
from rest_framework.viewsets import ModelViewSet
from django_display_ids.contrib.rest_framework import DisplayIDLookupMixin

class InvoiceViewSet(DisplayIDLookupMixin, ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    lookup_url_kwarg = "id"
    lookup_strategies = ("display_id", "uuid", "slug")
    display_id_prefix = "inv"
```

Now your views accept:
- `inv_2aUyqjCzEIiEcYMKj7TZtw` (display ID)
- `550e8400-e29b-41d4-a716-446655440000` (UUID)
- `my-invoice-slug` (slug)

**Templates:**

```django
{% load display_ids %}

{{ invoice.display_id }}                       {# inv_2aUyqjCzEIiEcYMKj7TZtw #}
{{ order.customer_id|display_id:"cust" }}      {# encode any UUID #}
```

## Features

- **Multiple identifier formats**: display ID (`prefix_base62uuid`), UUID (v4/v7), slug
- **Framework support**: Django CBVs and Django REST Framework
- **Template filter**: Encode UUIDs as display IDs in templates
- **Zero model changes required**: Works with any existing UUID field
- **OpenAPI integration**: Automatic schema generation with drf-spectacular

## Documentation

Full documentation at [django-display-ids.readthedocs.io](https://django-display-ids.readthedocs.io/).

## Contributing

See the [contributing guide](https://django-display-ids.readthedocs.io/en/latest/contributing.html).

## Related Projects

If you need ID generation and storage (custom model fields), consider:

- **[django-prefix-id](https://github.com/jaddison/django-prefix-id)** — PrefixIDField that generates and stores base62-encoded UUIDs
- **[django-spicy-id](https://github.com/mik3y/django-spicy-id)** — Drop-in AutoField replacement
- **[django-charid-field](https://github.com/yunojuno/django-charid-field)** — CharField wrapper supporting cuid, ksuid, ulid

**django-display-ids** works with existing UUID fields and handles resolution only — no migrations required.
