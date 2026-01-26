# django-display-ids

Stripe-like prefixed IDs for Django. Works with existing UUIDs — no schema changes.

Display IDs are human-friendly identifiers like `inv_2aUyqjCzEIiEcYMKj7TZtw` — a short prefix indicating the object type, followed by a base62-encoded UUID. This format, popularized by Stripe, makes IDs recognizable at a glance while remaining URL-safe and compact.

This library focuses on **lookup only** — it works with your existing UUID fields and requires no migrations or schema changes.

## Installation

```bash
pip install django-display-ids
```

No `INSTALLED_APPS` entry required — just import and use.

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

Now your view accepts both formats:
- `inv_2aUyqjCzEIiEcYMKj7TZtw` (display ID)
- `550e8400-e29b-41d4-a716-446655440000` (UUID)

## Features

- **Multiple identifier formats**: display ID (`prefix_base62uuid`), UUID (v4/v7), slug
- **Framework support**: Django CBVs and Django REST Framework
- **Zero model changes required**: Works with any existing UUID field
- **Stateless**: Pure lookup, no database writes

## Usage

### Django Class-Based Views

```python
from django.views.generic import DetailView, UpdateView, DeleteView
from django_display_ids import DisplayIDObjectMixin

class InvoiceDetailView(DisplayIDObjectMixin, DetailView):
    model = Invoice
    lookup_param = "id"
    lookup_strategies = ("display_id", "uuid")
    display_id_prefix = "inv"

# Works with any view that uses get_object()
class InvoiceUpdateView(DisplayIDObjectMixin, UpdateView):
    model = Invoice
    lookup_param = "id"
    display_id_prefix = "inv"
```

### Django REST Framework

```python
from rest_framework.viewsets import ModelViewSet
from django_display_ids.contrib.rest_framework import DisplayIDLookupMixin

class InvoiceViewSet(DisplayIDLookupMixin, ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    lookup_url_kwarg = "id"
    lookup_strategies = ("display_id", "uuid")
    display_id_prefix = "inv"
```

Or with APIView:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django_display_ids.contrib.rest_framework import DisplayIDLookupMixin

class InvoiceView(DisplayIDLookupMixin, APIView):
    lookup_url_kwarg = "id"
    lookup_strategies = ("display_id", "uuid")
    display_id_prefix = "inv"

    def get_queryset(self):
        return Invoice.objects.all()

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()
        return Response({"id": str(invoice.id)})
```

### Model Mixin

Add a `display_id` property to your models:

```python
import uuid
from django.db import models
from django_display_ids import DisplayIDMixin

class Invoice(DisplayIDMixin, models.Model):
    display_id_prefix = "inv"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

invoice = Invoice.objects.first()
invoice.display_id  # -> "inv_2aUyqjCzEIiEcYMKj7TZtw"
```

### Model Manager

```python
from django_display_ids import DisplayIDMixin, DisplayIDManager

class Invoice(DisplayIDMixin, models.Model):
    display_id_prefix = "inv"
    objects = DisplayIDManager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

# Get by display ID
invoice = Invoice.objects.get_by_display_id("inv_2aUyqjCzEIiEcYMKj7TZtw")

# Get by any identifier type
invoice = Invoice.objects.get_by_identifier("inv_2aUyqjCzEIiEcYMKj7TZtw")
invoice = Invoice.objects.get_by_identifier("550e8400-e29b-41d4-a716-446655440000")

# Works with filtered querysets
invoice = Invoice.objects.filter(active=True).get_by_identifier("inv_xxx")
```

### Django Admin

Enable searching by display ID or raw UUID in the admin:

```python
from django.contrib import admin
from django_display_ids import DisplayIDSearchMixin

@admin.register(Invoice)
class InvoiceAdmin(DisplayIDSearchMixin, admin.ModelAdmin):
    list_display = ["id", "display_id", "name", "created"]
    search_fields = ["name"]  # display_id/UUID search is automatic
```

Now you can search by either format in the admin search box:
- `inv_2aUyqjCzEIiEcYMKj7TZtw` (display ID)
- `550e8400-e29b-41d4-a716-446655440000` (raw UUID from logs)

The mixin automatically detects the UUID field from your model's `uuid_field`
attribute (if using `DisplayIDMixin`), or defaults to `id`. Override with:

```python
class InvoiceAdmin(DisplayIDSearchMixin, admin.ModelAdmin):
    uuid_field = "uid"  # custom UUID field name
```

### Encoding and Decoding

```python
import uuid
from django_display_ids import encode_display_id, decode_display_id

# Create a display ID from a UUID
invoice_id = uuid.uuid4()
display_id = encode_display_id("inv", invoice_id)
# -> "inv_2aUyqjCzEIiEcYMKj7TZtw"

# Decode back to prefix and UUID
prefix, decoded_uuid = decode_display_id(display_id)
```

### Direct Resolution

```python
from django_display_ids import resolve_object

invoice = resolve_object(
    model=Invoice,
    value="inv_2aUyqjCzEIiEcYMKj7TZtw",
    strategies=("display_id", "uuid", "slug"),
    prefix="inv",
)
```

## Identifier Formats

| Format | Example | Description |
|--------|---------|-------------|
| Display ID | `inv_2aUyqjCzEIiEcYMKj7TZtw` | Prefix + base62-encoded UUID |
| UUID | `550e8400-e29b-41d4-a716-446655440000` | Standard UUID (v4/v7) |
| Slug | `my-invoice-slug` | Human-readable identifier |

Display ID format:
- Prefix: 1-16 lowercase letters
- Separator: underscore
- Encoded UUID: 22 base62 characters (fixed length)

## Lookup Strategies

Strategies are tried in order. The first successful match is returned.

| Strategy | Description |
|----------|-------------|
| `display_id` | Decode display ID, lookup by UUID field |
| `uuid` | Parse as UUID, lookup by UUID field |
| `slug` | Lookup by slug field |

Default: `("display_id", "uuid")`

The slug strategy is a catch-all, so it should always be last.

The `display_id` strategy requires a prefix. If no prefix is configured, the strategy is skipped.

## Configuration

### View/Mixin Attributes

| Attribute | Default | Description |
|-----------|---------|-------------|
| `lookup_param` / `lookup_url_kwarg` | `"pk"` | URL parameter name |
| `lookup_strategies` | from settings | Strategies to try |
| `display_id_prefix` | `None` | Expected prefix |
| `uuid_field` | `"id"` | UUID field name on model |
| `slug_field` | `"slug"` | Slug field name on model |

### Django Settings (Optional)

All settings have sensible defaults. Only add this if you need to override them:

```python
# settings.py
DISPLAY_IDS = {
    "UUID_FIELD": "id",                     # default
    "SLUG_FIELD": "slug",                   # default
    "STRATEGIES": ("display_id", "uuid"),   # default
}
```

## Error Handling

| Exception | When Raised |
|-----------|-------------|
| `InvalidIdentifierError` | Identifier cannot be parsed |
| `UnknownPrefixError` | Display ID prefix doesn't match expected |
| `ObjectNotFoundError` | No matching database record |

In views, errors are converted to HTTP responses:
- Django CBV: `Http404`
- DRF: `NotFound` (404) or `ParseError` (400)

## Requirements

- Python 3.12+
- Django 4.2+
- Django REST Framework 3.14+ (optional)

## Development

Clone the repository and install dependencies:

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
uvx nox -p
```

Lint and format:

```bash
uvx pre-commit run --all-files
```

## Related Projects

If you need ID generation and storage (custom model fields), consider these alternatives:

- **[django-prefix-id](https://github.com/jaddison/django-prefix-id)** — PrefixIDField that generates and stores base62-encoded UUIDs
- **[django-spicy-id](https://github.com/mik3y/django-spicy-id)** — Drop-in AutoField replacement that displays numeric IDs as prefixed strings
- **[django-charid-field](https://github.com/yunojuno/django-charid-field)** — CharField wrapper supporting cuid, ksuid, ulid, and other generators

**django-display-ids** takes a different approach: it works with your existing UUID fields and handles resolution only. No migrations, no schema changes — just add the mixin to your views.

## License

ISC
