"""Tests for examples module."""

import uuid

import pytest

from django_display_ids.encoding import decode_display_id
from django_display_ids.examples import (
    example_display_id,
    example_uuid,
)

from .models import Invoice, Order


class TestExampleUuid:
    def test_known_value(self):
        """Pinned so docs and OpenAPI examples stay stable across releases."""
        assert example_uuid("app") == uuid.UUID("a172cedc-ae47-474b-615c-54d510a5d84a")

    def test_different_prefixes_produce_different_uuids(self):
        assert len({example_uuid(p) for p in ("inv", "user", "prod")}) == 3

    def test_accepts_model_class(self):
        assert example_uuid(Invoice) == example_uuid("inv")

    def test_model_without_prefix_raises(self):
        with pytest.raises(ValueError, match="has no display_id_prefix"):
            example_uuid(Order)


class TestExampleDisplayId:
    def test_known_value(self):
        """Pinned so docs and OpenAPI examples stay stable across releases."""
        assert example_display_id("app") == "app_4ueEO5Nz4X7u9qc3FVHokM"

    @pytest.mark.parametrize("prefix", ["a", "inv", "abcdefghijklmnop"])
    def test_decodes_to_example_uuid(self, prefix):
        assert decode_display_id(example_display_id(prefix)) == (
            prefix,
            example_uuid(prefix),
        )

    def test_accepts_model_class(self):
        assert example_display_id(Invoice) == example_display_id("inv")

    def test_model_without_prefix_raises(self):
        with pytest.raises(ValueError, match="has no display_id_prefix"):
            example_display_id(Order)
