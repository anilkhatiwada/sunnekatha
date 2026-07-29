"""Production settings. Required values intentionally fail fast."""

from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
ADMIN_ENVIRONMENT = "PRODUCTION"
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405
APP_VERSION = env("APP_VERSION")  # noqa: F405
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405
CORS_ALLOW_CREDENTIALS = env.bool(  # noqa: F405
    "CORS_ALLOW_CREDENTIALS",
    default=False,
)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
DATABASE_URL = env("DATABASE_URL")  # noqa: F405
REDIS_URL = env("REDIS_URL")  # noqa: F405
CELERY_BROKER_URL = env("CELERY_BROKER_URL")  # noqa: F405
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")  # noqa: F405
DATABASE_SSL_MODE = env("DATABASE_SSL_MODE", default="require")  # noqa: F405
ALLOW_INSECURE_REDIS = env.bool("ALLOW_INSECURE_REDIS", default=False)  # noqa: F405
DRF_NUM_PROXIES = env.int("DRF_NUM_PROXIES", default=1)  # noqa: F405
CLOUDFRONT_MEDIA_ENABLED = env.bool(  # noqa: F405
    "CLOUDFRONT_MEDIA_ENABLED",
    default=True,
)

if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY == "unsafe-development-key-change-before-production"
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a random value of at least 50 characters."
    )
if not APP_VERSION or APP_VERSION == "0.1.0":
    raise ImproperlyConfigured(
        "APP_VERSION must identify the immutable production release."
    )
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set for production.")
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Wildcard production hosts are not allowed.")
if any(not origin.startswith("https://") for origin in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured("Production CORS origins must use HTTPS.")
if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Production CSRF trusted origins must use HTTPS.")
if not USE_S3_STORAGE:  # noqa: F405
    raise ImproperlyConfigured("USE_S3_STORAGE must be enabled in production.")
if not AWS_S3_AUDIO_BUCKET_NAME:  # noqa: F405
    raise ImproperlyConfigured("AWS_S3_AUDIO_BUCKET_NAME is required.")
if not AWS_S3_COVER_BUCKET_NAME:  # noqa: F405
    raise ImproperlyConfigured("AWS_S3_COVER_BUCKET_NAME is required.")
if CLOUDFRONT_MEDIA_ENABLED:
    if not CLOUDFRONT_MEDIA_DOMAIN:  # noqa: F405
        raise ImproperlyConfigured("CLOUDFRONT_MEDIA_DOMAIN is required.")
    if not CLOUDFRONT_KEY_PAIR_ID:  # noqa: F405
        raise ImproperlyConfigured("CLOUDFRONT_KEY_PAIR_ID is required.")
    if not CLOUDFRONT_PRIVATE_KEY:  # noqa: F405
        raise ImproperlyConfigured("CLOUDFRONT_PRIVATE_KEY is required.")
if AWS_S3_ENDPOINT_URL:  # noqa: F405
    raise ImproperlyConfigured(
        "AWS_S3_ENDPOINT_URL must be unset when using AWS S3 in production."
    )
if not 30 <= CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS <= 900:  # noqa: F405
    raise ImproperlyConfigured(
        "CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS must be between 30 and 900."
    )
if not 1 <= DRF_NUM_PROXIES <= 10:
    raise ImproperlyConfigured("DRF_NUM_PROXIES must be between 1 and 10.")
database_url = urlparse(DATABASE_URL)
if database_url.scheme not in {"postgres", "postgresql"}:
    raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL.")
if DATABASE_SSL_MODE not in {"disable", "require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured(
        "DATABASE_SSL_MODE must be disable, require, verify-ca, or verify-full."
    )
if DATABASE_SSL_MODE == "disable" and database_url.hostname not in {
    "localhost",
    "127.0.0.1",
    "::1",
}:
    raise ImproperlyConfigured(
        "DATABASE_SSL_MODE may be disabled only for a loopback PostgreSQL host."
    )
for setting_name, value in {
    "REDIS_URL": REDIS_URL,
    "CELERY_BROKER_URL": CELERY_BROKER_URL,
    "CELERY_RESULT_BACKEND": CELERY_RESULT_BACKEND,
}.items():
    scheme = urlparse(value).scheme
    if scheme not in ({"redis", "rediss"} if ALLOW_INSECURE_REDIS else {"rediss"}):
        raise ImproperlyConfigured(
            f"{setting_name} must use rediss:// unless ALLOW_INSECURE_REDIS=true."
        )

DATABASES["default"]["CONN_MAX_AGE"] = env.int(  # noqa: F405
    "DATABASE_CONN_MAX_AGE",
    default=60,
)
if not 0 <= DATABASES["default"]["CONN_MAX_AGE"] <= 600:  # noqa: F405
    raise ImproperlyConfigured(
        "DATABASE_CONN_MAX_AGE must be between 0 and 600 seconds."
    )
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
DATABASES["default"]["OPTIONS"].update(  # noqa: F405
    {
        "connect_timeout": env.int(  # noqa: F405
            "DATABASE_CONNECT_TIMEOUT_SECONDS",
            default=5,
        ),
        "sslmode": DATABASE_SSL_MODE,
    }
)

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
WHITENOISE_MAX_AGE = env.int("STATIC_MAX_AGE_SECONDS", default=31536000)  # noqa: F405
WHITENOISE_KEEP_ONLY_HASHED_FILES = True

TRUST_X_FORWARDED_PROTO = env.bool(  # noqa: F405
    "TRUST_X_FORWARDED_PROTO",
    default=True,
)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if TRUST_X_FORWARDED_PROTO else None
)
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)  # noqa: F405
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_REDIRECT_EXEMPT = [
    r"^api/v1/health/$",
    r"^api/v1/readiness/$",
]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_NAME = "__Host-sunnekatha_sessionid"
CSRF_COOKIE_NAME = "__Host-sunnekatha_csrftoken"
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

LOGGING["formatters"]["json"] = {  # noqa: F405
    "()": "apps.common.logging.JsonFormatter",
}
DJANGO_LOG_FORMAT = env("DJANGO_LOG_FORMAT", default="json")  # noqa: F405
if DJANGO_LOG_FORMAT not in {"json", "simple"}:
    raise ImproperlyConfigured("DJANGO_LOG_FORMAT must be json or simple.")
LOGGING["handlers"]["console"]["formatter"] = DJANGO_LOG_FORMAT  # noqa: F405
REST_FRAMEWORK["NUM_PROXIES"] = DRF_NUM_PROXIES  # noqa: F405

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT = env.int(  # noqa: F405
    "CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT_SECONDS",
    default=30,
)
CELERY_WORKER_ENABLE_SOFT_SHUTDOWN_ON_IDLE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = env.int(  # noqa: F405
    "CELERY_WORKER_PREFETCH_MULTIPLIER",
    default=1,
)
CELERY_TASK_SOFT_TIME_LIMIT = env.int(  # noqa: F405
    "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS",
    default=300,
)
CELERY_TASK_TIME_LIMIT = env.int(  # noqa: F405
    "CELERY_TASK_TIME_LIMIT_SECONDS",
    default=360,
)
if CELERY_TASK_SOFT_TIME_LIMIT >= CELERY_TASK_TIME_LIMIT:
    raise ImproperlyConfigured(
        "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS must be less than "
        "CELERY_TASK_TIME_LIMIT_SECONDS."
    )
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": env.int(  # noqa: F405
        "CELERY_VISIBILITY_TIMEOUT_SECONDS",
        default=900,
    )
}
