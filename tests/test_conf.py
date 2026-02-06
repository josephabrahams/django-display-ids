"""Tests for configuration module."""

import pytest
from django.test import override_settings

from django_display_ids.conf import DEFAULTS, get_setting


class TestGetSetting:
    """Tests for get_setting function."""

    def test_defaults(self):
        """Default values are returned when not configured."""
        assert get_setting("UUID_FIELD") == "id"
        assert get_setting("SLUG_FIELD") == "slug"
        assert get_setting("STRATEGIES") == ("display_id", "uuid", "slug")

    def test_unknown_setting_raises_error(self):
        """KeyError raised for unknown setting name."""
        with pytest.raises(KeyError, match="Unknown setting"):
            get_setting("UNKNOWN_SETTING")

    @override_settings(DISPLAY_IDS={"UUID_FIELD": "uuid"})
    def test_custom_uuid_field(self):
        """Custom UUID_FIELD is returned."""
        assert get_setting("UUID_FIELD") == "uuid"

    @override_settings(DISPLAY_IDS={"SLUG_FIELD": "handle"})
    def test_custom_slug_field(self):
        """Custom SLUG_FIELD is returned."""
        assert get_setting("SLUG_FIELD") == "handle"

    @override_settings(DISPLAY_IDS={"STRATEGIES": ("uuid", "slug")})
    def test_custom_strategies(self):
        """Custom STRATEGIES is returned."""
        assert get_setting("STRATEGIES") == ("uuid", "slug")

    @override_settings(DISPLAY_IDS={})
    def test_empty_settings_uses_defaults(self):
        """Empty DISPLAY_IDS dict uses defaults."""
        assert get_setting("UUID_FIELD") == "id"
        assert get_setting("SLUG_FIELD") == "slug"
        assert get_setting("STRATEGIES") == ("display_id", "uuid", "slug")

    @override_settings(DISPLAY_IDS={"UUID_FIELD": "custom_id"})
    def test_partial_override(self):
        """Partial override keeps other defaults."""
        assert get_setting("UUID_FIELD") == "custom_id"
        assert get_setting("SLUG_FIELD") == "slug"  # Still default


class TestDefaults:
    """Tests for DEFAULTS constant."""

    def test_defaults_has_required_keys(self):
        """DEFAULTS contains all required keys."""
        assert "UUID_FIELD" in DEFAULTS
        assert "SLUG_FIELD" in DEFAULTS
        assert "STRATEGIES" in DEFAULTS

    def test_default_values(self):
        """Default values are correct."""
        assert DEFAULTS["UUID_FIELD"] == "id"
        assert DEFAULTS["SLUG_FIELD"] == "slug"
        assert DEFAULTS["STRATEGIES"] == ("display_id", "uuid", "slug")
