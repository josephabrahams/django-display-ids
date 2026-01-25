"""Django settings for tests."""

SECRET_KEY = "test-secret-key-not-for-production"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "tests",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Default display ID settings
DISPLAY_IDS = {
    "UUID_FIELD": "id",
    "SLUG_FIELD": "slug",
    "STRATEGIES": ("display_id", "uuid"),
}
