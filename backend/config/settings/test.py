"""Fast, isolated settings for automated tests."""

from .base import *  # noqa: F403

DEBUG = False
ADMIN_ENVIRONMENT = "LOCAL"
SECRET_KEY = "test-only-secret-key-with-at-least-thirty-two-bytes"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sunnekatha-tests",
    }
}

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
