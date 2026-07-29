"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True
ADMIN_ENVIRONMENT = "LOCAL"
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["https://*.ngrok-free.app"]
CACHES["default"]["OPTIONS"]["IGNORE_EXCEPTIONS"] = True  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer"
]
