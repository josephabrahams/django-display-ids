# Changelog

## 0.5.0 — 2026-02-05

- **Django-native exception hierarchy**: Exceptions now inherit from both `DisplayIDLookupError` and a standard Django/Python exception, so existing `except` clauses catch them naturally:
  - `ObjectNotFoundError` extends `ObjectDoesNotExist`
  - `InvalidIdentifierError` extends `ValueError`
  - `UnknownPrefixError` extends `ValueError`
  - `MissingPrefixError` extends `ImproperlyConfigured`
  - `AmbiguousIdentifierError` extends `MultipleObjectsReturned`
- **QuerySet methods raise `Model.DoesNotExist`**: `get_by_identifier()` and `get_by_display_id()` now raise `Model.DoesNotExist` and `Model.MultipleObjectsReturned`, matching Django's `QuerySet.get()` contract. The typed exceptions (`ObjectNotFoundError`, etc.) are still used by lower-level functions like `resolve_object()`.
- **Safe slug strategy**: Include `"slug"` in the default `STRATEGIES` setting (`("display_id", "uuid", "slug")`). The slug strategy is now automatically skipped for models without a slug field, so it's safe to include globally.
- **QuerySet type preservation**: `DisplayIDQuerySet` chainable methods (`filter()`, `exclude()`, `select_related()`, etc.) now return `Self`, so display ID methods remain visible to type checkers after chaining.

## 0.4.1 — 2026-02-05

- Accept `str | UUID` in `get_by_identifier()`, `get_by_display_id()`, `get_by_identifiers()`, and `resolve_object()`. When a `UUID` object is passed, strategy parsing is skipped and a direct UUID lookup is performed.
- Built-in `DisplayIDOrSlugConverter` and `DisplayIDOrUUIDOrSlugConverter` now respect the `DISPLAY_IDS["SLUG_REGEX"]` setting, consistent with the factory functions.

## 0.4.0 — 2026-02-02

- Rename `get_by_display_id_or_uuid()` → `get_by_identifier()` and `get_by_display_ids_or_uuids()` → `get_by_identifiers()`.
- Move `id_param_description` to `contrib.drf_spectacular`.

## 0.3.2 — 2026-02-02

- Add slug support to URL path converters (`DisplayIDOrSlugConverter`, `DisplayIDOrUUIDOrSlugConverter`, and factory functions).

## 0.3.1 — 2026-01-31

- Fix `display_id` property crash when UUID is `None`.
- Validate queryset in manager methods.

## 0.3.0 — 2026-01-31

- Add URL path converters (`DisplayIDConverter`, `DisplayIDOrUUIDConverter`).
- Add `display_id` template filter.
- Add batch lookup support (`get_by_identifiers()`).
- Add mypy strict mode with django-stubs.

## 0.2.0 — 2026-01-28

- Add Read the Docs documentation.

## 0.1.4 — 2026-01-26

- Add `DisplayIDField` and drf-spectacular integration.

## 0.1.3 — 2026-01-25

- Inherit `display_id_prefix` from parent model.

## 0.1.2 — 2026-01-25

- Update package metadata.

## 0.1.1 — 2026-01-25

- Add `DisplayIDSearchMixin` for Django admin.

## 0.1.0 — 2026-01-25

- Initial release with `DisplayIDModel`, `DisplayIDManager`, Base62 encoding, and DRF serializer support.
