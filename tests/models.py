"""Test models for django-display-ids tests."""

import uuid

from django.db import models

from django_display_ids import DisplayIDManager, DisplayIDModel


class Invoice(DisplayIDModel, models.Model):
    """Test model with display ID support."""

    display_id_prefix = "inv"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    slug = models.SlugField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)

    objects = DisplayIDManager()

    class Meta:
        app_label = "tests"


class Product(DisplayIDModel, models.Model):
    """Test model with custom field names."""

    display_id_prefix = "prod"
    uuid_field = "uid"
    slug_field = "handle"

    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    handle = models.SlugField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)

    objects = DisplayIDManager()

    class Meta:
        app_label = "tests"


class Order(models.Model):
    """Test model without DisplayIDModel (no prefix)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    slug = models.SlugField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)

    objects = DisplayIDManager()

    class Meta:
        app_label = "tests"


class Tag(DisplayIDModel, models.Model):
    """Test model without a slug field."""

    display_id_prefix = "tag"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)

    objects = DisplayIDManager()

    class Meta:
        app_label = "tests"


class LineItem(models.Model):
    """Test model with relations to display ID models.

    invoice points at a model whose UUID is the primary key; products at one
    whose UUID is a separate field. Its own primary key is an integer, with
    the UUID in uid.
    """

    uuid_field = "uid"

    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True)
    products = models.ManyToManyField(Product, blank=True)
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "tests"
