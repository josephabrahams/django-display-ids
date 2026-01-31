"""Tests for template tags and filters."""

from __future__ import annotations

import uuid

import pytest
from django.template import Context, Template, TemplateSyntaxError

from django_display_ids.encoding import encode_display_id

from .models import Invoice


class TestDisplayIdFilter:
    """Tests for the display_id filter."""

    def test_filter_with_uuid(self) -> None:
        """Filter encodes a UUID with prefix."""
        test_uuid = uuid.uuid4()
        t = Template('{% load display_ids %}{{ my_uuid|display_id:"inv" }}')
        result = t.render(Context({"my_uuid": test_uuid}))
        assert result == encode_display_id("inv", test_uuid)

    @pytest.mark.django_db
    def test_filter_with_model_uuid_field(self) -> None:
        """Filter works with UUID field from model."""
        invoice = Invoice.objects.create(name="Test")
        t = Template('{% load display_ids %}{{ invoice.id|display_id:"inv" }}')
        result = t.render(Context({"invoice": invoice}))
        assert result == encode_display_id("inv", invoice.id)

    @pytest.mark.django_db
    def test_filter_with_foreign_key_uuid(self) -> None:
        """Filter works with foreign key UUID."""
        # Simulating a foreign key UUID scenario
        customer_id = uuid.uuid4()
        t = Template('{% load display_ids %}{{ customer_id|display_id:"cust" }}')
        result = t.render(Context({"customer_id": customer_id}))
        assert result == encode_display_id("cust", customer_id)

    def test_filter_with_none_returns_empty(self) -> None:
        """Filter returns empty string for None."""
        t = Template('{% load display_ids %}{{ my_uuid|display_id:"inv" }}')
        result = t.render(Context({"my_uuid": None}))
        assert result == ""

    def test_filter_with_invalid_prefix(self) -> None:
        """Filter raises error for invalid prefix format."""
        test_uuid = uuid.uuid4()
        t = Template('{% load display_ids %}{{ my_uuid|display_id:"INVALID" }}')
        with pytest.raises(TemplateSyntaxError, match="lowercase letters"):
            t.render(Context({"my_uuid": test_uuid}))

    def test_filter_with_non_uuid_raises(self) -> None:
        """Filter raises error when value is not a UUID."""
        t = Template('{% load display_ids %}{{ obj|display_id:"inv" }}')
        with pytest.raises(TemplateSyntaxError, match="requires a UUID"):
            t.render(Context({"obj": "not-a-uuid"}))

    def test_filter_with_integer_raises(self) -> None:
        """Filter raises error for integer value."""
        t = Template('{% load display_ids %}{{ obj|display_id:"inv" }}')
        with pytest.raises(TemplateSyntaxError, match="requires a UUID"):
            t.render(Context({"obj": 12345}))

    @pytest.mark.django_db
    def test_filter_in_loop(self) -> None:
        """Filter works correctly in a loop."""
        uuids = [uuid.uuid4() for _ in range(3)]
        t = Template(
            "{% load display_ids %}"
            '{% for u in uuids %}{{ u|display_id:"inv" }},{% endfor %}'
        )
        result = t.render(Context({"uuids": uuids}))
        expected = ",".join(encode_display_id("inv", u) for u in uuids) + ","
        assert result == expected


class TestTemplatetagRegistration:
    """Tests for template tag library registration."""

    def test_library_loads(self) -> None:
        """Template library can be loaded."""
        t = Template("{% load display_ids %}")
        t.render(Context())

    def test_filter_registered(self) -> None:
        """display_id filter is registered."""
        from django_display_ids.templatetags.display_ids import register

        assert "display_id" in register.filters
