"""Minimal settings used only to collect immutable static assets in the image."""

from .base import *  # noqa: F403

DEBUG = False
ADMIN_ENVIRONMENT = "LOCAL"
SECRET_KEY = "image-build-only-not-used-at-runtime"

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
