import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.common.logging import JsonFormatter

BACKEND_DIR = Path(__file__).resolve().parents[3]


def production_environment(**overrides):
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "APP_VERSION": "2026.07.23+test",
        "DJANGO_SECRET_KEY": "test-only-A7$k9!" * 4,
        "DJANGO_ALLOWED_HOSTS": "api.example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
        "CSRF_TRUSTED_ORIGINS": "https://app.example.com",
        "DATABASE_URL": "postgresql://user:password@database:5432/sunnekatha",
        "DATABASE_SSL_MODE": "require",
        "REDIS_URL": "rediss://cache.example.com:6379/1",
        "CELERY_BROKER_URL": "rediss://cache.example.com:6379/2",
        "CELERY_RESULT_BACKEND": "rediss://cache.example.com:6379/3",
        "USE_S3_STORAGE": "true",
        "AWS_S3_AUDIO_BUCKET_NAME": "private-audio",
        "AWS_S3_COVER_BUCKET_NAME": "private-covers",
        "AWS_CLOUDFRONT_DOMAIN": "media.example.com",
        "CLOUDFRONT_MEDIA_DOMAIN": "audio.example.com",
        "CLOUDFRONT_KEY_PAIR_ID": "KTEST",
        "CLOUDFRONT_PRIVATE_KEY": "test-only-private-key",
        "AWS_S3_ENDPOINT_URL": "",
    }
    environment.update(overrides)
    return environment


def run_settings(environment):
    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import django, json; django.setup(); "
                "from django.conf import settings; "
                "print(json.dumps({"
                "'engine': settings.DATABASES['default']['ENGINE'], "
                "'sslmode': settings.DATABASES['default']['OPTIONS']['sslmode'], "
                "'conn_max_age': settings.DATABASES['default']['CONN_MAX_AGE'], "
                "'cache': settings.CACHES['default']['BACKEND'], "
                "'static': settings.STORAGES['staticfiles']['BACKEND'], "
                "'num_proxies': settings.REST_FRAMEWORK['NUM_PROXIES'], "
                "'middleware': settings.MIDDLEWARE[1]"
                "}))"
            ),
        ],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_settings_use_postgres_redis_whitenoise_and_connection_reuse():
    result = run_settings(production_environment())

    assert result.returncode == 0, result.stderr
    configured = json.loads(result.stdout)
    assert configured == {
        "engine": "django.db.backends.postgresql",
        "sslmode": "require",
        "conn_max_age": 60,
        "cache": "django_redis.cache.RedisCache",
        "static": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        "num_proxies": 1,
        "middleware": "whitenoise.middleware.WhiteNoiseMiddleware",
    }


def test_production_settings_allow_loopback_postgres_without_tls():
    result = run_settings(
        production_environment(
            DATABASE_URL="postgresql://user:password@127.0.0.1:5432/sunnekatha",
            DATABASE_SSL_MODE="disable",
        )
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sslmode"] == "disable"


def test_production_settings_allow_staged_cloudfront_configuration():
    result = run_settings(
        production_environment(
            CLOUDFRONT_MEDIA_ENABLED="false",
            AWS_CLOUDFRONT_DOMAIN="",
            CLOUDFRONT_MEDIA_DOMAIN="",
            CLOUDFRONT_KEY_PAIR_ID="",
            CLOUDFRONT_PRIVATE_KEY="",
        )
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"DJANGO_SECRET_KEY": "short"}, "DJANGO_SECRET_KEY"),
        ({"DATABASE_URL": "sqlite:///unsafe.sqlite3"}, "PostgreSQL"),
        ({"REDIS_URL": "redis://cache:6379/1"}, "rediss://"),
        ({"DJANGO_ALLOWED_HOSTS": "*"}, "Wildcard"),
        ({"APP_VERSION": "0.1.0"}, "APP_VERSION"),
        ({"DATABASE_CONN_MAX_AGE": "-1"}, "DATABASE_CONN_MAX_AGE"),
        ({"DJANGO_LOG_FORMAT": "unsafe"}, "DJANGO_LOG_FORMAT"),
        ({"DRF_NUM_PROXIES": "0"}, "DRF_NUM_PROXIES"),
        (
            {
                "DATABASE_URL": ("postgresql://user:password@database:5432/sunnekatha"),
                "DATABASE_SSL_MODE": "disable",
            },
            "loopback PostgreSQL",
        ),
        (
            {
                "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS": "400",
                "CELERY_TASK_TIME_LIMIT_SECONDS": "360",
            },
            "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS",
        ),
    ],
)
def test_production_settings_fail_fast_for_unsafe_environment(override, expected):
    result = run_settings(production_environment(**override))

    assert result.returncode != 0
    assert expected in result.stderr


def test_json_formatter_emits_machine_readable_unicode_log():
    record = logging.LogRecord(
        "sunnekatha.test",
        logging.INFO,
        __file__,
        1,
        "नेपाली सन्देश",
        (),
        None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "sunnekatha.test"
    assert payload["message"] == "नेपाली सन्देश"
    assert payload["timestamp"].endswith("+00:00")
