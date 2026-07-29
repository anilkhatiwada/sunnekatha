"""Settings shared by every SunneKatha backend environment."""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab
from django.templatetags.static import static
from django.urls import reverse_lazy

from config.admin import (
    admin_changelist_url,
    admin_index_url,
    admin_model_permission,
    failed_processing_url,
    scheduled_publications_url,
    staff_permission,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BACKEND_DIR.parent

env = environ.Env(
    APP_VERSION=(str, "0.1.0"),
    HOME_PUBLIC_CACHE_TIMEOUT=(int, 300),
    FEATURED_CACHE_TIMEOUT=(int, 300),
    TAXONOMY_CACHE_TIMEOUT=(int, 900),
    PUBLIC_DETAIL_CACHE_TIMEOUT=(int, 300),
    ADMIN_DASHBOARD_CACHE_TIMEOUT=(int, 60),
    DATA_UPLOAD_MAX_MEMORY_SIZE=(int, 2 * 1024 * 1024),
    FILE_UPLOAD_MAX_MEMORY_SIZE=(int, 2 * 1024 * 1024),
    DATA_UPLOAD_MAX_NUMBER_FIELDS=(int, 200),
    ANALYTICS_MAX_RANGE_DAYS=(int, 366),
    ANALYTICS_PRIVACY_MIN_LISTENERS=(int, 2),
    ADMIN_ENVIRONMENT=(str, ""),
    DEBUG=(bool, False),
    DATABASE_CONN_MAX_AGE=(int, 60),
    DJANGO_LOG_LEVEL=(str, "INFO"),
)

env_file = BACKEND_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="unsafe-development-key-change-before-production",
)
DEBUG = env.bool("DEBUG")
APP_VERSION = env("APP_VERSION")
HOME_PUBLIC_CACHE_TIMEOUT = env.int("HOME_PUBLIC_CACHE_TIMEOUT")
FEATURED_CACHE_TIMEOUT = env.int("FEATURED_CACHE_TIMEOUT")
TAXONOMY_CACHE_TIMEOUT = env.int("TAXONOMY_CACHE_TIMEOUT")
PUBLIC_DETAIL_CACHE_TIMEOUT = env.int("PUBLIC_DETAIL_CACHE_TIMEOUT")
ADMIN_DASHBOARD_CACHE_TIMEOUT = env.int("ADMIN_DASHBOARD_CACHE_TIMEOUT")
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE")
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE")
DATA_UPLOAD_MAX_NUMBER_FIELDS = env.int("DATA_UPLOAD_MAX_NUMBER_FIELDS")
DATA_UPLOAD_MAX_NUMBER_FILES = env.int("DATA_UPLOAD_MAX_NUMBER_FILES", default=10)
ANALYTICS_MAX_RANGE_DAYS = env.int("ANALYTICS_MAX_RANGE_DAYS")
ANALYTICS_PRIVACY_MIN_LISTENERS = env.int("ANALYTICS_PRIVACY_MIN_LISTENERS")
ADMIN_ENVIRONMENT = env("ADMIN_ENVIRONMENT").strip().upper()
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "storages",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.analytics",
    "apps.authors",
    "apps.catalog",
    "apps.common",
    "apps.creators",
    "apps.explore",
    "apps.home",
    "apps.library",
    "apps.media_access",
    "apps.narrators",
    "apps.notifications",
    "apps.playlists",
    "apps.search",
    "apps.subscriptions",
    "apps.taxonomy",
    "apps.uploads",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

UNFOLD = {
    "SITE_TITLE": "SunneKatha Administration",
    "SITE_HEADER": "SunneKatha",
    "SITE_SUBHEADER": "Audio Literature Management",
    "SITE_ICON": lambda request: static("admin/brand/sunnekatha-monogram.svg"),
    "SITE_SYMBOL": "auto_stories",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "any",
            "type": "image/svg+xml",
            "href": lambda request: static("admin/brand/sunnekatha-favicon.svg"),
        }
    ],
    "ENVIRONMENT": "config.admin.environment_callback",
    "ENVIRONMENT_TITLE_PREFIX": "config.admin.environment_title_prefix_callback",
    "DASHBOARD_CALLBACK": "config.admin.dashboard_callback",
    "STYLES": [
        lambda request: static("admin/css/sunnekatha-responsive.css"),
    ],
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "base": {
            "50": "oklch(97.5% .008 70)",
            "100": "oklch(94% .012 65)",
            "200": "oklch(87% .02 60)",
            "300": "oklch(75% .03 55)",
            "400": "oklch(62% .035 50)",
            "500": "oklch(50% .032 48)",
            "600": "oklch(39% .028 45)",
            "700": "oklch(30% .025 42)",
            "800": "oklch(23% .022 40)",
            "900": "oklch(18% .018 38)",
            "950": "oklch(13% .014 35)",
        },
        "primary": {
            "50": "oklch(97% .018 78)",
            "100": "oklch(93% .04 75)",
            "200": "oklch(87% .07 72)",
            "300": "oklch(79% .10 68)",
            "400": "oklch(72% .13 60)",
            "500": "oklch(66% .16 50)",
            "600": "oklch(59% .18 43)",
            "700": "oklch(51% .15 40)",
            "800": "oklch(43% .11 38)",
            "900": "oklch(36% .08 36)",
            "950": "oklch(25% .05 34)",
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-700)",
            "default-dark": "var(--color-base-200)",
            "important-light": "var(--color-base-950)",
            "important-dark": "var(--color-base-50)",
        },
    },
    "LOGIN": {
        "image": lambda request: static("admin/brand/sunnekatha-login.svg"),
    },
    "COMMAND": {
        "search_models": True,
        "show_history": False,
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Dashboard",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Overview",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                        "permission": staff_permission,
                    }
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Literary Works",
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:catalog_literarywork_changelist"),
                        "permission": admin_model_permission("catalog", "literarywork"),
                    },
                    {
                        "title": "Audio Tracks",
                        "icon": "graphic_eq",
                        "link": reverse_lazy("admin:catalog_audiotrack_changelist"),
                        "permission": admin_model_permission("catalog", "audiotrack"),
                    },
                    {
                        "title": "Albums",
                        "icon": "album",
                        "link": reverse_lazy("admin:catalog_album_changelist"),
                        "permission": admin_model_permission("catalog", "album"),
                    },
                    {
                        "title": "Authors",
                        "icon": "person",
                        "link": reverse_lazy("admin:authors_author_changelist"),
                        "permission": admin_model_permission("authors", "author"),
                    },
                    {
                        "title": "Narrators",
                        "icon": "record_voice_over",
                        "link": reverse_lazy("admin:narrators_narrator_changelist"),
                        "permission": admin_model_permission("narrators", "narrator"),
                    },
                ],
            },
            {
                "title": "Editorial",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Pending Reviews",
                        "icon": "rate_review",
                        "link": reverse_lazy(
                            "admin:catalog_pendingreviewtrack_changelist"
                        ),
                        "permission": "config.admin.editorial_review_permission",
                        "badge": "config.admin.pending_review_badge",
                        "badge_variant": "warning",
                    },
                    {
                        "title": "Playlists",
                        "icon": "queue_music",
                        "link": reverse_lazy("admin:playlists_playlist_changelist"),
                        "permission": admin_model_permission("playlists", "playlist"),
                    },
                    {
                        "title": "Homepage Sections",
                        "icon": "home",
                        "link": reverse_lazy("admin:home_homesection_changelist"),
                        "permission": admin_model_permission("home", "homesection"),
                    },
                    {
                        "title": "Featured Content",
                        "icon": "star",
                        "link": admin_changelist_url(
                            "admin:catalog_audiotrack_changelist",
                            is_featured__exact="1",
                        ),
                        "permission": admin_model_permission("catalog", "audiotrack"),
                    },
                    {
                        "title": "Scheduled Publications",
                        "icon": "schedule",
                        "link": scheduled_publications_url,
                        "permission": admin_model_permission("catalog", "audiotrack"),
                        "badge": "config.admin.scheduled_publications_badge",
                        "badge_variant": "warning",
                    },
                ],
            },
            {
                "title": "Taxonomy",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Genres",
                        "icon": "category",
                        "link": reverse_lazy("admin:taxonomy_genre_changelist"),
                        "permission": admin_model_permission("taxonomy", "genre"),
                    },
                    {
                        "title": "Moods",
                        "icon": "mood",
                        "link": reverse_lazy("admin:taxonomy_mood_changelist"),
                        "permission": admin_model_permission("taxonomy", "mood"),
                    },
                    {
                        "title": "Languages",
                        "icon": "language",
                        "link": reverse_lazy("admin:taxonomy_language_changelist"),
                        "permission": admin_model_permission("taxonomy", "language"),
                    },
                    {
                        "title": "Categories",
                        "icon": "account_tree",
                        "link": reverse_lazy(
                            "admin:taxonomy_contentcategory_changelist"
                        ),
                        "permission": admin_model_permission(
                            "taxonomy", "contentcategory"
                        ),
                    },
                ],
            },
            {
                "title": "Audio Operations",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Upload Sessions",
                        "icon": "cloud_upload",
                        "link": reverse_lazy("admin:uploads_uploadsession_changelist"),
                        "permission": admin_model_permission(
                            "uploads", "uploadsession"
                        ),
                        "badge": "config.admin.pending_upload_badge",
                        "badge_variant": "info",
                    },
                    {
                        "title": "Processing Queue",
                        "icon": "pending_actions",
                        "link": admin_changelist_url(
                            "admin:catalog_audioprocessingjob_changelist",
                            processing_state="queued",
                        ),
                        "permission": admin_model_permission(
                            "catalog", "audioprocessingjob"
                        ),
                        "badge": "config.admin.processing_queue_badge",
                        "badge_variant": "info",
                    },
                    {
                        "title": "Failed Processing",
                        "icon": "error",
                        "link": failed_processing_url,
                        "permission": admin_model_permission(
                            "catalog", "audioprocessingjob"
                        ),
                        "badge": "config.admin.failed_processing_badge",
                        "badge_variant": "danger",
                    },
                    {
                        "title": "Media Files",
                        "icon": "audio_file",
                        "link": reverse_lazy("admin:catalog_audiotrack_changelist"),
                        "permission": admin_model_permission("catalog", "audiotrack"),
                    },
                ],
            },
            {
                "title": "Rights",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Copyright Licenses",
                        "icon": "copyright",
                        "link": reverse_lazy(
                            "admin:catalog_copyrightlicense_changelist"
                        ),
                        "permission": admin_model_permission(
                            "catalog", "copyrightlicense"
                        ),
                    },
                    {
                        "title": "Rights Holders",
                        "icon": "verified_user",
                        "link": reverse_lazy("admin:catalog_rightsholder_changelist"),
                        "permission": admin_model_permission("catalog", "rightsholder"),
                    },
                    {
                        "title": "Permission Documents",
                        "icon": "description",
                        "link": reverse_lazy(
                            "admin:catalog_permissiondocument_changelist"
                        ),
                        "permission": admin_model_permission(
                            "catalog", "permissiondocument"
                        ),
                    },
                ],
            },
            {
                "title": "Audience",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "group",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                        "permission": admin_model_permission("accounts", "user"),
                    },
                    {
                        "title": "Listening Progress",
                        "icon": "resume",
                        "link": reverse_lazy(
                            "admin:library_listeningprogress_changelist"
                        ),
                        "permission": admin_model_permission(
                            "library", "listeningprogress"
                        ),
                    },
                    {
                        "title": "Playback History",
                        "icon": "history",
                        "link": reverse_lazy(
                            "admin:library_listeninghistory_changelist"
                        ),
                        "permission": admin_model_permission(
                            "library", "listeninghistory"
                        ),
                    },
                    {
                        "title": "Subscriptions",
                        "icon": "workspace_premium",
                        "link": reverse_lazy(
                            "admin:subscriptions_usersubscription_changelist"
                        ),
                        "permission": admin_model_permission(
                            "subscriptions", "usersubscription"
                        ),
                    },
                ],
            },
            {
                "title": "System",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Staff",
                        "icon": "admin_panel_settings",
                        "link": admin_changelist_url(
                            "admin:accounts_user_changelist",
                            is_staff__exact="1",
                        ),
                        "permission": admin_model_permission("accounts", "user"),
                    },
                    {
                        "title": "Groups",
                        "icon": "groups",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": admin_model_permission("auth", "group"),
                    },
                    {
                        "title": "Permissions",
                        "icon": "key",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": admin_model_permission("auth", "group"),
                    },
                    {
                        "title": "Administrative Audit",
                        "icon": "history",
                        "link": reverse_lazy(
                            "admin:common_administrativeaudit_changelist"
                        ),
                        "permission": admin_model_permission(
                            "common", "administrativeaudit"
                        ),
                    },
                    {
                        "title": "Metadata Transfer",
                        "icon": "sync_alt",
                        "link": reverse_lazy("admin_metadata_transfer"),
                        "permission": lambda request: (
                            request.user.has_perm("common.import_metadata")
                            or request.user.has_perm("common.export_metadata")
                        ),
                    },
                    {
                        "title": "Analytics Dashboard",
                        "icon": "monitoring",
                        "link": reverse_lazy("admin:analytics_dashboard"),
                        "permission": admin_model_permission(
                            "analytics", "dailyplatformmetric"
                        ),
                    },
                    {
                        "title": "Application Settings",
                        "icon": "settings",
                        "link": admin_index_url,
                        "permission": staff_permission,
                    },
                ],
            },
        ],
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.request_context.RequestIdentifierMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BACKEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://sunnekatha:sunnekatha@localhost:5432/sunnekatha",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE")
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": not env.bool(
                "REDIS_RAISE_EXCEPTIONS",
                default=not DEBUG,
            ),
        },
        "KEY_PREFIX": "sunnekatha",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BACKEND_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BACKEND_DIR / "media"
USE_S3_STORAGE = env.bool("USE_S3_STORAGE", default=False)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
AWS_S3_AUDIO_BUCKET_NAME = env("AWS_S3_AUDIO_BUCKET_NAME", default="")
AWS_S3_COVER_BUCKET_NAME = env("AWS_S3_COVER_BUCKET_NAME", default="")
AWS_CLOUDFRONT_DOMAIN = env("AWS_CLOUDFRONT_DOMAIN", default="")
AWS_QUERYSTRING_EXPIRE = env.int("AWS_QUERYSTRING_EXPIRE", default=900)
CLOUDFRONT_MEDIA_DOMAIN = env(
    "CLOUDFRONT_MEDIA_DOMAIN",
    default=AWS_CLOUDFRONT_DOMAIN,
)
CLOUDFRONT_KEY_PAIR_ID = env("CLOUDFRONT_KEY_PAIR_ID", default="")
CLOUDFRONT_PRIVATE_KEY = env("CLOUDFRONT_PRIVATE_KEY", default="")
CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS = env.int(
    "CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS",
    default=300,
)
UPLOAD_SESSION_EXPIRY_SECONDS = env.int(
    "UPLOAD_SESSION_EXPIRY_SECONDS",
    default=900,
)

if USE_S3_STORAGE:
    _shared_s3_options = {
        "region_name": AWS_S3_REGION_NAME,
        "endpoint_url": AWS_S3_ENDPOINT_URL,
        "file_overwrite": False,
        "default_acl": "private",
        "querystring_expire": AWS_QUERYSTRING_EXPIRE,
    }
    STORAGES = {
        "default": {
            "BACKEND": "apps.common.storage.CoverImageStorage",
            "OPTIONS": {
                **_shared_s3_options,
                "bucket_name": AWS_S3_COVER_BUCKET_NAME,
                "custom_domain": AWS_CLOUDFRONT_DOMAIN or None,
            },
        },
        "original_audio": {
            "BACKEND": "apps.common.storage.PrivateOriginalAudioStorage",
            "OPTIONS": {
                **_shared_s3_options,
                "bucket_name": AWS_S3_AUDIO_BUCKET_NAME,
            },
        },
        "processed_audio": {
            "BACKEND": "apps.common.storage.PrivateProcessedAudioStorage",
            "OPTIONS": {
                **_shared_s3_options,
                "bucket_name": AWS_S3_AUDIO_BUCKET_NAME,
            },
        },
        "temporary_uploads": {
            "BACKEND": "apps.common.storage.TemporaryUploadStorage",
            "OPTIONS": {
                **_shared_s3_options,
                "bucket_name": AWS_S3_AUDIO_BUCKET_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "apps.common.storage.LocalCoverImageStorage",
        },
        "original_audio": {
            "BACKEND": "apps.common.storage.LocalOriginalAudioStorage",
        },
        "processed_audio": {
            "BACKEND": "apps.common.storage.LocalProcessedAudioStorage",
        },
        "temporary_uploads": {
            "BACKEND": "apps.common.storage.LocalTemporaryUploadStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
MAX_IMAGE_UPLOAD_BYTES = env.int(
    "MAX_IMAGE_UPLOAD_BYTES",
    default=10 * 1024 * 1024,
)
MAX_PERMISSION_DOCUMENT_BYTES = env.int(
    "MAX_PERMISSION_DOCUMENT_BYTES",
    default=20 * 1024 * 1024,
)
MAX_AUDIO_UPLOAD_BYTES = env.int(
    "MAX_AUDIO_UPLOAD_BYTES",
    default=500 * 1024 * 1024,
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
CORS_URLS_REGEX = r"^/api/.*$"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": ("apps.common.pagination.StandardPageNumberPagination"),
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.errors.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_ANON_THROTTLE_RATE", default="100/hour"),
        "user": env("DRF_USER_THROTTLE_RATE", default="1000/hour"),
        "registration": env("DRF_REGISTRATION_THROTTLE_RATE", default="3/hour"),
        "login": env("DRF_LOGIN_THROTTLE_RATE", default="5/minute"),
        "token_refresh": env("DRF_TOKEN_REFRESH_THROTTLE_RATE", default="30/minute"),
        "password_change": env(
            "DRF_PASSWORD_CHANGE_THROTTLE_RATE",
            default="5/hour",
        ),
        "upload": env("DRF_UPLOAD_THROTTLE_RATE", default="30/hour"),
        "stream": env("DRF_STREAM_THROTTLE_RATE", default="120/hour"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SunneKatha API",
    "DESCRIPTION": (
        "Production API for the SunneKatha audio-first Nepali literature platform.\n\n"
        "Authenticated endpoints use a JWT access token in the "
        "`Authorization: Bearer <access-token>` header. Refresh tokens are rotated "
        "and the previous refresh token is blacklisted. Collection responses use "
        "the `{count, next, previous, results}` page envelope unless an operation "
        "documents an aggregated response.\n\n"
        "Errors use the stable `{detail, code, errors?}` envelope. Validation "
        "errors include field-level details in `errors`."
    ),
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "TAGS": [
        {"name": "auth", "description": "JWT authentication and account management."},
        {"name": "uploads", "description": "Secure direct-to-S3 upload sessions."},
        {"name": "tracks", "description": "Track discovery and media authorization."},
        {
            "name": "me",
            "description": "Authenticated listener state and synchronization.",
        },
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "CHECK_REVOKE_TOKEN": True,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL"),
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL"),
            "propagate": False,
        },
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/2")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/3",
)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULE = {
    "aggregate-previous-day-analytics": {
        "task": "apps.analytics.tasks.aggregate_daily_analytics",
        "schedule": crontab(minute=15, hour=2),
    }
}
