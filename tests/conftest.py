"""Shared fixtures. Test files that need fixed IDs or slugs define their own."""

import pytest

from .models import Invoice, Order, Product, Tag


@pytest.fixture
def invoice(db):
    return Invoice.objects.create(name="Test Invoice", slug="test-invoice")


@pytest.fixture
def product(db):
    """Product keeps its UUID in uid and its slug in handle."""
    return Product.objects.create(name="Test Product", handle="test-product")


@pytest.fixture
def order(db):
    """Order has no display_id_prefix."""
    return Order.objects.create(name="Test Order", slug="test-order")


@pytest.fixture
def tag(db):
    """Tag has no slug field."""
    return Tag.objects.create(name="Test Tag")
