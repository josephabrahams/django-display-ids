"""Tests for template tags and filters."""

from __future__ import annotations

import uuid

import pytest
from django.template import Context, Template, TemplateSyntaxError

from django_display_ids.encoding import encode_display_id

from .models import Invoice


def render(value, prefix="inv"):
    template = Template(
        f'{{% load display_ids %}}{{{{ value|display_id:"{prefix}" }}}}'
    )
    return template.render(Context({"value": value}))


class TestDisplayIdFilter:
    def test_uuid(self) -> None:
        test_uuid = uuid.uuid4()
        assert render(test_uuid) == encode_display_id("inv", test_uuid)

    @pytest.mark.django_db
    def test_model_uuid_field(self) -> None:
        invoice = Invoice.objects.create(name="Test")
        template = Template('{% load display_ids %}{{ invoice.id|display_id:"inv" }}')
        assert template.render(Context({"invoice": invoice})) == invoice.display_id

    @pytest.mark.parametrize(
        "value",
        [
            "550e8400-e29b-41d4-a716-446655440000",
            "550E8400-E29B-41D4-A716-446655440000",
            " 550e8400-e29b-41d4-a716-446655440000 ",
        ],
    )
    def test_uuid_string(self, value) -> None:
        """Filter accepts UUID strings, like the lookup functions do."""
        assert render(value) == "inv_2aUyqjCzEIiEcYMKj7TZtw"

    def test_none_returns_empty(self) -> None:
        assert render(None) == ""

    def test_invalid_prefix(self) -> None:
        with pytest.raises(TemplateSyntaxError, match="lowercase letters"):
            render(uuid.uuid4(), prefix="INVALID")

    @pytest.mark.parametrize(
        ("value", "message"),
        [
            ("not-a-uuid", "display_id filter"),
            ("", "display_id filter"),
            ("550e8400e29b41d4a716446655440000", "Invalid UUID"),
            (12345, "got int"),
        ],
    )
    def test_non_uuid_raises(self, value, message) -> None:
        """Only None renders as empty; other non-UUIDs, including "", raise."""
        with pytest.raises(TemplateSyntaxError, match=message):
            render(value)

    def test_in_loop(self) -> None:
        uuids = [uuid.uuid4() for _ in range(3)]
        template = Template(
            "{% load display_ids %}"
            '{% for u in uuids %}{{ u|display_id:"inv" }},{% endfor %}'
        )
        expected = ",".join(encode_display_id("inv", u) for u in uuids) + ","
        assert template.render(Context({"uuids": uuids})) == expected
