"""Tests for the system checks.

Models with a broken configuration are defined inside isolate_apps, so they
don't join the app registry the other tests use.
"""

import uuid

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.checks import run_checks
from django.db import models
from django.test.utils import isolate_apps

from django_display_ids import DisplayIDAdminSearchMixin, DisplayIDModel

from .models import Invoice, LineItem, Order


def check_ids(messages):
    return [m.id for m in messages if m.id.startswith("display_ids.")]


def test_test_models_pass():
    assert check_ids(run_checks()) == []


class TestModelUUIDField:
    @isolate_apps("tests")
    def test_missing_field(self):
        class Missing(DisplayIDModel):
            display_id_prefix = "ckmissing"
            uuid_field = "uid"

        assert check_ids(Missing.check()) == ["display_ids.W001"]

    @isolate_apps("tests")
    def test_integer_primary_key(self):
        """The default uuid_field is "id", which is an integer here."""

        class IntegerKey(DisplayIDModel):
            display_id_prefix = "ckinteger"

        assert check_ids(IntegerKey.check()) == ["display_ids.W001"]

    @isolate_apps("tests")
    def test_foreign_key_to_a_uuid(self):
        """display_id reads the attribute, which is an object, not a UUID."""

        class Child(DisplayIDModel):
            display_id_prefix = "ckchild"
            uuid_field = "invoice"
            invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)

        assert check_ids(Child.check()) == ["display_ids.W001"]

    @isolate_apps("tests")
    def test_no_prefix_needs_no_uuid(self):
        class NoPrefix(DisplayIDModel):
            name = models.CharField(max_length=10)

        assert check_ids(NoPrefix.check()) == []

    @isolate_apps("tests")
    def test_separate_uuid_field(self):
        class Separate(DisplayIDModel):
            display_id_prefix = "ckseparate"
            uuid_field = "uid"
            uid = models.UUIDField(default=uuid.uuid4)

        assert check_ids(Separate.check()) == []


class TestModelSlugUnique:
    @isolate_apps("tests")
    def test_not_unique(self):
        class Loose(DisplayIDModel):
            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            slug = models.SlugField()

        assert check_ids(Loose.check()) == ["display_ids.W002"]

    @isolate_apps("tests")
    def test_unique_constraint_with_other_fields(self):
        """Unique per tenant counts: lookups run on a tenant's rows."""

        class PerTenant(DisplayIDModel):
            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            tenant = models.IntegerField()
            slug = models.SlugField()

            class Meta:
                constraints = (
                    models.UniqueConstraint(
                        fields=["tenant", "slug"], name="unique_slug"
                    ),
                )

        assert check_ids(PerTenant.check()) == []

    @isolate_apps("tests")
    def test_conditional_unique_constraint(self):
        """Unique among rows that aren't deleted counts: the default manager
        usually hides deleted rows."""

        class SoftDeleted(DisplayIDModel):
            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            slug = models.SlugField()
            deleted = models.BooleanField(default=False)

            class Meta:
                constraints = (
                    models.UniqueConstraint(
                        fields=["slug"],
                        condition=models.Q(deleted=False),
                        name="unique_live_slug",
                    ),
                )

        assert check_ids(SoftDeleted.check()) == []

    @isolate_apps("tests")
    def test_unique_together(self):
        class Together(DisplayIDModel):
            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            tenant = models.IntegerField()
            slug = models.SlugField()

            class Meta:
                unique_together = (("tenant", "slug"),)

        assert check_ids(Together.check()) == []

    @isolate_apps("tests")
    def test_slug_strategy_off(self, settings):
        settings.DISPLAY_IDS = {"STRATEGIES": ("display_id", "uuid")}

        class Loose(DisplayIDModel):
            id = models.UUIDField(primary_key=True, default=uuid.uuid4)
            slug = models.SlugField()

        assert check_ids(Loose.check()) == []


def admin_check(model, **attrs):
    admin_class = type(
        "Admin",
        (DisplayIDAdminSearchMixin, admin.ModelAdmin),
        {"search_fields": ("name",), **attrs},
    )
    return check_ids(admin_class(model, AdminSite()).check())


class TestAdmin:
    def test_valid(self):
        assert admin_check(Invoice) == []

    @isolate_apps("tests")
    def test_model_without_uuid(self):
        """The mixin on a model with only an integer key (RefillGenie's case)."""

        class Plain(models.Model):
            name = models.CharField(max_length=10)

        assert admin_check(Plain) == ["display_ids.W003"]

    def test_uuid_field_option(self):
        assert admin_check(Invoice, uuid_field="name") == ["display_ids.W003"]

    def test_slug_only_does_not_need_a_uuid(self):
        options = {"uuid_field": "name", "lookup_strategies": ("slug",)}
        assert admin_check(Invoice, **options) == []

    def test_lookup_that_cannot_work(self):
        """Order has no prefix, so display_id alone can never match."""
        options = {"lookup_strategies": ("display_id",)}
        assert admin_check(Order, **options) == ["display_ids.W005"]

    @pytest.mark.parametrize(
        "path", ["uid", "invoice", "invoice_id", "invoice__id", "products__uid"]
    )
    def test_search_field_ends_at_uuid(self, path):
        fields = {path: None}
        assert admin_check(LineItem, display_id_search_fields=fields) == []

    @isolate_apps("tests")
    def test_generic_foreign_key(self):
        """A GenericForeignKey has no single column to compare, so it warns."""

        class Tagged(models.Model):
            content_type = models.ForeignKey(
                "contenttypes.ContentType", on_delete=models.CASCADE
            )
            object_id = models.UUIDField()
            target = GenericForeignKey("content_type", "object_id")
            name = models.CharField(max_length=10)

        fields = {"target": None, "object_id": None}
        assert admin_check(Tagged, display_id_search_fields=fields) == [
            "display_ids.W003",  # Tagged's own id is an integer
            "display_ids.W004",
        ]

    @pytest.mark.parametrize(
        "path", ["nope", "id", "name", "products", "invoice__name", "uid__nope"]
    )
    def test_search_field_not_a_uuid(self, path):
        """products compares Product's integer key, not its uid."""
        fields = {path: None}
        assert admin_check(LineItem, display_id_search_fields=fields) == [
            "display_ids.W004"
        ]
