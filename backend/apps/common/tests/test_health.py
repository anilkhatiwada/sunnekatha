from unittest.mock import patch

from django.db import DatabaseError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_health_check_reports_liveness_without_database_access():
    response = APIClient().get(reverse("common:health"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_readiness_check_reports_ready(db):
    response = APIClient().get(reverse("common:readiness"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "cache": "ok"},
    }


def test_readiness_check_reports_database_failure():
    with patch(
        "apps.common.views.connection.cursor",
        side_effect=DatabaseError("database unavailable"),
    ):
        response = APIClient().get(reverse("common:readiness"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "detail": "A required dependency is unavailable.",
        "code": "service_unavailable",
        "errors": {"database": ["Database connection failed."]},
    }


def test_readiness_check_reports_cache_failure(db):
    with patch(
        "apps.common.views.cache.set",
        side_effect=ConnectionError("cache unavailable"),
    ):
        response = APIClient().get(reverse("common:readiness"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["errors"] == {"cache": ["Cache connection failed."]}


def test_application_version_is_available(settings):
    settings.APP_VERSION = "1.2.3"

    response = APIClient().get(reverse("common:version"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"version": "1.2.3"}
