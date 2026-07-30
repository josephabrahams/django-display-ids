# Changelog

## 0.7.1 — 2026-07-30

- **`DisplayIDAdminSearchMixin` strips surrounding whitespace**: `_parse_identifier()` now strips leading and trailing whitespace before parsing, so a display ID pasted from a terminal, email, or log line still matches. Previously a padded display ID failed to decode and the admin search silently returned no results; raw UUIDs were unaffected because `uuid.UUID()` already tolerates whitespace. Interior whitespace is untouched, so Django's multi-word `search_fields` behavior is unchanged.

## 0.7.0 — 2026-05-18

- **`DisplayIDField` gains a `prefix_from=` kwarg**: Derives the prefix from a referenced model class (`DisplayIDField(prefix_from=App)`) instead of restating the string. Use it when the serialized row is a projection of another model (e.g. a database-view-backed report row) that mirrors that model's data but carries no `display_id_prefix` of its own. `prefix` and `prefix_from` are mutually exclusive, and `prefix_from` is validated at initialization — pointing it at a class with no `display_id_prefix` raises `ValueError` at app startup, not on the first request.
- **`DisplayIDField` honors `required=False`**: When no prefix can be resolved for an instance, the field returns `None` instead of raising. Use this for serializers that handle heterogeneous rows, only some of which carry a prefix. The default remains `required=True` (raise) so misconfiguration still fails loudly.

## 0.6.2 — 2026-03-29

- **`parse_identifier()` accepts display IDs without a prefix**: `expected_prefix=None` now means "accept any valid prefix" instead of "skip display_id strategy." This makes `parse_identifier` usable standalone without requiring a prefix. `resolve_object()` still skips display_id for models without a prefix — that policy moved from the parser to the resolver.

## 0.6.1 — 2026-03-28

- **`resolve_object()` auto-detects `prefix`**: Completes the auto-detection started in 0.6.0. When `prefix` is not passed (or ``None``), `resolve_object()` reads `model.display_id_prefix` automatically. This means `resolve_object(Invoice, identifier)` just works — no need to pass prefix, field names, or strategies. To skip the `display_id` strategy, omit it from `strategies` instead of passing `prefix=None`.
- **Removed `_get_display_id_prefix()` from view mixins**: Both `DisplayIDMixin` (Django) and `DisplayIDMixin` (DRF) no longer define this method — prefix resolution is now handled by `resolve_object()`.
- **`resolve_object()` accepts `model` and `value` as positional args**: `resolve_object(Invoice, identifier)` now works. Optional parameters (`strategies`, `prefix`, `uuid_field`, `slug_field`, `queryset`) remain keyword-only.
- **Removed `NOT_SET` sentinel from `conf`**: No longer needed now that all parameters use `None` for auto-detection.

## 0.6.0 — 2026-03-28

- **`resolve_object()` auto-detects `uuid_field` and `slug_field`**: When either parameter is not explicitly passed, `resolve_object()` now checks the model's class attribute (set by `DisplayIDModel`), then the `DISPLAY_IDS` setting, then falls back to `"id"` / `"slug"`. This matches the resolution order already used by `DisplayIDAdminSearchMixin`, `DisplayIDMixin`, and `DisplayIDManager`. Callers no longer need to manually resolve and pass these for models that declare them.
- **`DisplayIDAdminSearchMixin` respects `DISPLAY_IDS["UUID_FIELD"]` setting**: Previously fell back directly to `"id"`, skipping the global setting.
- **Removed `_get_uuid_field()` and `_get_slug_field()` from view mixins**: Both `DisplayIDMixin` (Django) and `DisplayIDMixin` (DRF) no longer define these internal methods — field resolution is now handled by `resolve_object()`.
- **Removed `get_uuid_field()` and `get_slug_field()` from `conf`**: These helpers are superseded by the auto-detection in `resolve_object()`.
- **Removed `example_uuid_for_prefix` and `example_display_id_for_prefix` aliases**: Use `example_uuid` and `example_display_id` directly — they accept both prefix strings and model classes.

## 0.5.5 — 2026-03-28

- **Security fix**: `DisplayIDAdminSearchMixin.get_search_results()` now filters against the incoming queryset instead of `self.model._default_manager`, preventing row leakage when used with tenant-scoped or otherwise filtered admin querysets.

## 0.5.4 — 2026-03-05

- **`_parse_identifier()` static method**: `DisplayIDAdminSearchMixin` now exposes a `_parse_identifier(search_term)` static method that parses a display ID or raw UUID and returns a `uuid.UUID` (or `None`). Subclasses can use this to search related UUID fields without re-implementing the decode logic.

## 0.5.3 — 2026-03-05

- **Admin raw UUID search**: `DisplayIDAdminSearchMixin` now recognizes raw UUIDs (with or without hyphens) and does an exact match against the UUID field. No need to add the UUID field to `search_fields`.

## 0.5.2 — 2026-02-05

- **MRO-friendly manager**: `DisplayIDManager` now sets `_queryset_class` instead of overriding `get_queryset()`, allowing custom managers to override `get_queryset()` without being shadowed in multi-inheritance scenarios.

## 0.5.1 — 2026-02-05

- **`resolve_identifier()` method**: Resolve an identifier (display ID, UUID, or slug) to a `uuid.UUID` value without fetching the full model instance. For UUID and display_id identifiers, the UUID is extracted by parsing alone — zero database queries. Only slug identifiers require a DB lookup. Useful for cursor-based pagination where you need a UUID for a `WHERE` clause but don't need the object.

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
