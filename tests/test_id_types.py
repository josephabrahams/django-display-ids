"""Tests for DisplayIDType, display IDs with no model behind them."""

import re
import uuid

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import isolate_apps

from django_display_ids import (
    DisplayIDModel,
    DisplayIDType,
    InvalidIdentifierError,
    UnknownPrefixError,
    encode_display_id,
    registry,
)

UID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch):
    """Types and models defined here mustn't leak into the global registry."""
    monkeypatch.setattr(registry, "_prefix_registry", dict(registry._prefix_registry))
    monkeypatch.setattr(registry, "_type_prefixes", set(registry._type_prefixes))


@pytest.fixture
def request_id():
    return DisplayIDType("req")


class TestPrefix:
    @pytest.mark.parametrize("prefix", ["", "Req", "req1", "waytoolongprefixxx"])
    def test_invalid_prefix(self, prefix):
        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            DisplayIDType(prefix)

    def test_model_prefix_is_taken(self):
        with pytest.raises(ValueError, match=r"already used by tests\.models\.Invoice"):
            DisplayIDType("inv")

    @isolate_apps("tests")
    def test_model_cannot_take_a_type_prefix(self, request_id):
        with pytest.raises(ValueError, match="already used by a DisplayIDType"):

            class Request(DisplayIDModel):
                display_id_prefix = "req"

    def test_types_can_share_a_prefix(self, request_id):
        """A module imported twice makes the same type again."""
        assert DisplayIDType("req").prefix == "req"

    def test_repr(self, request_id):
        assert repr(request_id) == "DisplayIDType('req')"


class TestGenerate:
    def test_factory(self):
        request_id = DisplayIDType("req", factory=lambda: UID)
        assert request_id.generate() == encode_display_id("req", UID)

    @pytest.mark.skipif(not hasattr(uuid, "uuid7"), reason="Python 3.14+")
    def test_uuid7_by_default(self, request_id):
        value = request_id.generate()
        assert value.startswith("req_")
        assert request_id.parse(value).version == 7

    def test_needs_a_factory_without_uuid7(self, request_id, monkeypatch):
        """No silent fallback to uuid4: that would change the IDs' ordering
        depending on the Python version."""
        monkeypatch.delattr(uuid, "uuid7", raising=False)
        with pytest.raises(ImproperlyConfigured, match="factory="):
            request_id.generate()

    def test_only_generate_needs_uuid7(self, request_id, monkeypatch):
        monkeypatch.delattr(uuid, "uuid7", raising=False)
        assert request_id.parse(request_id.encode(UID)) == UID


class TestEncodeAndParse:
    def test_encode(self, request_id):
        assert request_id.encode(UID) == encode_display_id("req", UID)
        assert request_id.encode(str(UID)) == encode_display_id("req", UID)

    def test_round_trip(self, request_id):
        assert request_id.parse(request_id.encode(UID)) == UID

    def test_parse_ignores_surrounding_whitespace(self, request_id):
        assert request_id.parse(f"  {request_id.encode(UID)}\n") == UID

    def test_parse_wrong_prefix(self, request_id):
        with pytest.raises(UnknownPrefixError):
            request_id.parse(encode_display_id("evt", UID))

    @pytest.mark.parametrize("value", ["req_short", "not an id", str(UID), ""])
    def test_parse_invalid(self, request_id, value):
        with pytest.raises(InvalidIdentifierError):
            request_id.parse(value)

    def test_errors_are_value_errors(self, request_id):
        """Existing `except ValueError` code keeps working."""
        with pytest.raises(ValueError):
            request_id.parse(encode_display_id("evt", UID))

    @pytest.mark.parametrize("value", [UID, None, 1])
    def test_parse_non_string(self, request_id, value):
        with pytest.raises(TypeError):
            request_id.parse(value)


class TestIsValid:
    def test_valid(self, request_id):
        assert request_id.is_valid(request_id.encode(UID))

    @pytest.mark.parametrize(
        "value",
        [encode_display_id("evt", UID), "req_short", str(UID), "", None, UID],
    )
    def test_invalid(self, request_id, value):
        assert request_id.is_valid(value) is False


class TestRegex:
    def test_matches_its_own_ids_only(self, request_id):
        assert re.fullmatch(request_id.regex, request_id.encode(UID))
        assert not re.fullmatch(request_id.regex, encode_display_id("evt", UID))
        assert not re.fullmatch(request_id.regex, "req_short")
