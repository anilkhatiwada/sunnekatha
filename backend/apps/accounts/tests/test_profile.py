import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "StrongPass!234"


def authenticated_client(user):
    client = APIClient()
    login = client.post(
        reverse("accounts:token"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client


def test_profile_update():
    user = UserFactory()
    client = authenticated_client(user)

    response = client.patch(
        reverse("accounts:profile"),
        {
            "email": "updated@example.com",
            "username": "updated-listener",
            "displayName": "परिवर्तित नाम",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["displayName"] == "परिवर्तित नाम"
    user.refresh_from_db()
    assert user.email == "updated@example.com"
    assert user.username == "updated-listener"


def test_preference_update():
    user = UserFactory()
    client = authenticated_client(user)

    response = client.patch(
        reverse("accounts:preferences"),
        {
            "preferredLanguage": "en",
            "defaultPlaybackSpeed": 1.5,
            "autoplayEnabled": False,
            "explicitContentEnabled": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["preferredLanguage"] == "en"
    assert response.data["defaultPlaybackSpeed"] == 1.5
    assert response.data["autoplayEnabled"] is False
    assert response.data["explicitContentEnabled"] is True


def test_preference_update_rejects_unsupported_speed():
    user = UserFactory()
    client = authenticated_client(user)

    response = client.patch(
        reverse("accounts:preferences"),
        {"defaultPlaybackSpeed": 3},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert "defaultPlaybackSpeed" in response.data["errors"]


def test_change_password_invalidates_old_credentials_and_refresh_token():
    user = UserFactory()
    client = authenticated_client(user)
    login = APIClient().post(
        reverse("accounts:token"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    new_password = "AnotherStrong!567"

    response = client.post(
        reverse("accounts:change-password"),
        {
            "currentPassword": PASSWORD,
            "newPassword": new_password,
            "newPasswordConfirm": new_password,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    old_login = APIClient().post(
        reverse("accounts:token"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED
    old_refresh = APIClient().post(
        reverse("accounts:token-refresh"),
        {"refresh": login.data["refresh"]},
        format="json",
    )
    assert old_refresh.status_code == status.HTTP_401_UNAUTHORIZED
    new_login = APIClient().post(
        reverse("accounts:token"),
        {"email": user.email, "password": new_password},
        format="json",
    )
    assert new_login.status_code == status.HTTP_200_OK
