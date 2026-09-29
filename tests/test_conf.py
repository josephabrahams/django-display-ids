"""Tests for configuration module."""

import pytest
from django.test import override_settings
from django.urls.converters import SlugConverter

from django_display_ids.conf import DEFAULTS, get_setting


class TestGetSetting:
    @override_settings(DISPLAY_IDS={})
    def test_defaults(self):
        assert get_setting("UUID_FIELD") == "id"
        assert get_setting("SLUG_FIELD") == "slug"
        assert get_setting("STRATEGIES") == ("display_id", "uuid", "slug")
        assert get_setting("SLUG_REGEX") == SlugConverter.regex

    def test_unknown_setting_raises_error(self):
        with pytest.raises(KeyError, match="Unknown setting"):
            get_setting("UNKNOWN_SETTING")

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("UUID_FIELD", "uuid"),
            ("SLUG_FIELD", "handle"),
            ("STRATEGIES", ("uuid", "slug")),
            ("SLUG_REGEX", r"[a-z]+"),
        ],
    )
    def test_override(self, name, value):
        with override_settings(DISPLAY_IDS={name: value}):
            assert get_setting(name) == value

    @override_settings(DISPLAY_IDS={"UUID_FIELD": "custom_id"})
    def test_partial_override_keeps_other_defaults(self):
        assert get_setting("UUID_FIELD") == "custom_id"
        assert get_setting("SLUG_FIELD") == "slug"


def test_defaults_cover_every_setting():
    assert set(DEFAULTS) == {"UUID_FIELD", "SLUG_FIELD", "STRATEGIES", "SLUG_REGEX"}
