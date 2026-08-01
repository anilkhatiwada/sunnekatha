from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def test_sensitive_endpoints_have_dedicated_throttle_scopes(settings):
    from apps.accounts.views import LoginView, RegistrationView
    from apps.catalog.track_views import TrackStreamView
    from apps.uploads.views import UploadSessionMixin

    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert RegistrationView.throttle_scope == "registration"
    assert LoginView.throttle_scope == "login"
    assert UploadSessionMixin.throttle_scope == "upload"
    assert TrackStreamView.throttle_scope == "stream"
    assert rates["registration"] == "3/hour"
    assert rates["login"] == "5/minute"
    assert rates["upload"] == "30/hour"
    assert rates["stream"] == "120/hour"


def test_general_api_throttles_support_normal_frontend_browsing(settings):
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    assert rates["anon"] == "1000/hour"
    assert rates["user"] == "5000/hour"


def test_registration_and_profile_reject_privileged_mass_assignment():
    registration = APIClient().post(
        reverse("accounts:register"),
        {
            "email": "secure@example.com",
            "username": "secure-user",
            "displayName": "Secure User",
            "password": "A-long-secure-password-984!",
            "passwordConfirm": "A-long-secure-password-984!",
            "isStaff": True,
            "isCreator": True,
        },
        format="json",
    )
    assert registration.status_code == 400
    assert registration.data["code"] == "validation_error"

    user = UserFactory(is_creator=False, is_staff=False)
    client = APIClient()
    client.force_authenticate(user)
    profile = client.patch(
        reverse("accounts:profile"),
        {"displayName": "Updated", "isStaff": True, "isCreator": True},
        format="json",
    )
    assert profile.status_code == 400
    user.refresh_from_db()
    assert not user.is_staff
    assert not user.is_creator


def test_request_and_cors_defaults_are_bounded(settings):
    assert settings.CORS_ALLOW_ALL_ORIGINS is False
    assert settings.CORS_URLS_REGEX == r"^/api/.*$"
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE <= 2 * 1024 * 1024
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE <= 2 * 1024 * 1024
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS <= 200
    assert settings.DATA_UPLOAD_MAX_NUMBER_FILES <= 10
    assert settings.SESSION_COOKIE_HTTPONLY


def test_player_media_response_is_not_shared_between_users():
    track = AudioTrackFactory(is_premium=True)
    entitled_user = UserFactory()
    entitled_client = APIClient()
    entitled_client.force_authenticate(entitled_user)
    url = reverse("catalog:track-player", args=[track.slug])

    def access_urls(_track, *, request):
        if request.user.is_authenticated:
            return {"high": "https://signed.example/private", "low": None}
        return {"high": None, "low": None}

    with patch(
        "apps.catalog.track_serializers.track_media_url_service.get_access_urls",
        side_effect=access_urls,
    ) as media_access:
        entitled = entitled_client.get(url)
        anonymous = APIClient().get(url)

    assert entitled.data["media"]["high"] == "https://signed.example/private"
    assert anonymous.data["media"]["high"] is None
    assert media_access.call_count == 2


def test_unhandled_errors_return_safe_generic_envelope():
    with patch(
        "apps.common.views.ApplicationVersionView.get",
        side_effect=RuntimeError("database password=do-not-leak"),
    ):
        response = APIClient(raise_request_exception=False).get(
            reverse("common:version")
        )

    assert response.status_code == 500
    assert response.data == {
        "detail": "An unexpected error occurred.",
        "code": "server_error",
    }
    assert "do-not-leak" not in str(response.data)
