"""CI settings using the real PostgreSQL and Redis service containers."""

from .base import *  # noqa: F403

DEBUG = False
ADMIN_ENVIRONMENT = "LOCAL"
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
