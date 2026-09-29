# Changelog

## Unreleased

### New

- `filter_by_identifier()` on the manager and queryset. It reads a display ID, UUID or slug like `get_by_identifier()`, but returns a queryset, which is empty when nothing matches.

## 0.8.0 — 2026-09-28

The views, DRF, managers, admin search and `resolve_object()` used to disagree about which identifiers they accepted. They now share one lookup, so a value that works in one works in all of them. This release also adds `DisplayIDRelatedField`, so DRF APIs can accept display IDs in request bodies.

### Breaking changes

- The Django view mixin's `lookup_param` is now `lookup_url_kwarg`, the name the DRF mixin already used. Rename it in your views. A view that still sets `lookup_param` raises `TypeError` when it's defined, so you'll find out at startup.
- The DRF mixin now runs `filter_queryset()` before looking up the object, as DRF's own `get_object()` does. Before, filter backends were skipped on detail lookups, so a backend that limits users to their own objects didn't apply there. An invalid identifier or wrong prefix is now a 404 instead of a 400. The mixin raises Django's `Http404` like DRF does, instead of `NotFound`; the response is the same, but tests that catch `NotFound` need updating.
- In both view mixins, a slug that matches more than one row raises `MultipleObjectsReturned` instead of returning a 404, as Django and DRF do. Keep slug fields unique. A missing URL parameter raises `AttributeError` (Django) or `AssertionError` (DRF) instead of a 404 or 400.
- A lookup that can never match now raises instead of treating everything as not found, for example `lookup_strategies = ("display_id",)` on a model without a prefix. It raises `MissingPrefixError`, or `ImproperlyConfigured` for a slug-only lookup on a model without the slug field. `get_by_display_id()` on a model without a prefix now raises for UUID objects too.
- The managers and admin search no longer match a display ID with another model's prefix. Before, searching `cust_...` in the invoice admin, or `Order.objects.get_by_identifier("inv_...")` on a model without a prefix, could return a row that happened to share the UUID.
- Admin search follows the `STRATEGIES` setting and adds exact slug matches, like the views. If your project limits `STRATEGIES`, admin search is limited the same way; set `lookup_strategies` on the `ModelAdmin` to override it.
- `get_by_identifiers()` leaves out invalid identifiers and wrong prefixes, as it already did for missing rows, instead of raising for the whole batch.
- `resolve_object()` and `id_param_description()` follow the `STRATEGIES` setting when not given strategies. Before, they used the built-in default.
- Two models with the same class name in different modules can no longer share a prefix. This now raises `ValueError` when the second model is defined.
- UUID strings must be in the standard hyphenated form, in either case, everywhere: lookups, admin search, converters, encoders and the template filter. 32 hex digits without hyphens, braces and `urn:uuid:` are no longer read as UUIDs; they're treated like any other string, so a slug like an MD5 hash can now be found. This includes `parse_identifier()` and `parse_uuid()` called directly, so check any code that passes them external input. It also changes what search boxes find: a UUID pasted without hyphens, as some database consoles print it, no longer matches in admin search or any other lookup, except as a slug. Before, they accepted any form `uuid.UUID()` does.
- The drf-spectacular extension no longer reads `display_id_prefix` from the serializer class, which `DisplayIDField` never used. Set `prefix=` or `prefix_from=` on the field instead.

### New

- `DisplayIDRelatedField` for DRF serializers: shows the related object's display ID and accepts a display ID, UUID or slug in requests. It supports `many=True` (one query for the whole list), takes the same lookup options as the view mixins, avoids a query per row when serializing if the UUID is the primary key, and has a drf-spectacular schema.
- The manager's `resolve_identifier()` is now `resolve_uuid()`, since it returns a UUID and `resolve_object()` returns an object. The old name still works but warns.
- `resolve_objects()` looks up many identifiers in one query and maps each one to its object, or `None`.
- The `<display_id_or_uuid:>` and `<identifier:>` converters accept uppercase UUIDs. `reverse()` accepts `uuid.UUID` objects.
- Surrounding whitespace is ignored everywhere, not only in admin search.
- `encode_uuid()`, `encode_display_id()` and the `display_id` template filter accept hyphenated UUID strings as well as UUID objects.
- drf-spectacular documents the `{id}` path parameter of `DisplayIDMixin` views: a string described by the view's own strategies, prefix and slug field, instead of the primary key's `format: uuid`, which display IDs failed. A parameter set with `@extend_schema` still wins.
- `id_param_description()` takes `strategies=`, and `None` as the prefix for models without one.
- `DisplayIDAdminSearchMixin` takes `lookup_strategies`, `display_id_prefix` and `slug_field`, like the view mixins. Its helper for searching other UUID fields is now public as `parse_search_uuid()`, and takes `model=` to apply that model's prefix. `_parse_identifier()` still works but warns.
- The Django view mixin works with only `queryset` set, without `model`.
- `pip install "django-display-ids[drf]"` and `"django-display-ids[spectacular]"` install the optional dependencies. Only Django is required, as before.
- Django 6.1 support.

### Fixes

- `DisplayIDOrSlugConverter` and `DisplayIDOrUUIDOrSlugConverter` read `SLUG_REGEX` when the URLs are loaded instead of at import, so `override_settings` affects them.
- `parse_uuid()` returned `None` for a `uuid.UUID` object, and `parse_slug()` treated one as a slug.
- The drf-spectacular extensions only registered if something imported `django_display_ids.contrib.drf_spectacular`, so `DisplayIDField` schemas were often missing. Importing the DRF integration now registers them.
- `DisplayIDField`'s OpenAPI pattern includes the prefix when it's known.
- The docs are rewritten and several errors are fixed, including wrong example values, `decode_display_id()`'s error type, and exception examples that weren't valid Python.

## 0.7.1 — 2026-07-30

- **`DisplayIDAdminSearchMixin` strips surrounding whitespace**: `_parse_identifier()` now strips leading and trailing whitespace before parsing, so a display ID pasted from a terminal, email, or log line still matches. Previously a padded display ID or UUID failed to parse and the admin search silently returned no results. Interior whitespace is untouched, so Django's multi-word `search_fields` behavior is unchanged.

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
