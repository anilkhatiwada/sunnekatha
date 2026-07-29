import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "StrongPass!234"


def authenticate(client, user, password=PASSWORD):
    response = client.post(
        reverse("accounts:token"),
        {"email": user.email, "password": password},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response


def test_registration_creates_user_and_returns_tokens():
    response = APIClient().post(
        reverse("accounts:register"),
        {
            "email": "New.Listener@Example.com",
            "username": "new-listener",
            "displayName": "नयाँ श्रोता",
            "password": PASSWORD,
            "passwordConfirm": PASSWORD,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert set(response.data) == {"access", "refresh", "user"}
    assert response.data["user"]["email"] == "new.listener@example.com"
    assert response.data["user"]["displayName"] == "नयाँ श्रोता"
    assert User.objects.get().check_password(PASSWORD)


def test_registration_rejects_case_insensitive_duplicate_email():
    UserFactory(email="listener@example.com")

    response = APIClient().post(
        reverse("accounts:register"),
        {
            "email": "LISTENER@example.com",
            "username": "another-listener",
            "displayName": "Another Listener",
            "password": PASSWORD,
            "passwordConfirm": PASSWORD,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert "email" in response.data["errors"]


def test_login_uses_email_and_returns_user():
    user = UserFactory(email="listener@example.com")

    response = APIClient().post(
        reverse("accounts:token"),
        {"email": "LISTENER@EXAMPLE.COM", "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data) == {"access", "refresh", "user"}
    assert response.data["user"]["id"] == str(user.id)


def test_login_rejects_invalid_credentials():
    user = UserFactory()

    response = APIClient().post(
        reverse("accounts:token"),
        {"email": user.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access" not in response.data
    assert response.data["code"] == "no_active_account"


def test_refresh_rotates_refresh_token():
    login = authenticate(APIClient(), UserFactory())

    response = APIClient().post(
        reverse("accounts:token-refresh"),
        {"refresh": login.data["refresh"]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["refresh"] != login.data["refresh"]


def test_logout_blacklists_refresh_token():
    client = APIClient()
    login = authenticate(client, UserFactory())

    response = client.post(
        reverse("accounts:logout"),
        {"refresh": login.data["refresh"]},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    refresh_response = APIClient().post(
        reverse("accounts:token-refresh"),
        {"refresh": login.data["refresh"]},
        format="json",
    )
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_protected_endpoint_requires_access_token():
    response = APIClient().get(reverse("accounts:me"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "not_authenticated"


def test_current_user_accepts_access_token():
    client = APIClient()
    user = UserFactory()
    authenticate(client, user)

    response = client.get(reverse("accounts:me"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email


def test_inactive_account_cannot_access_authenticated_endpoints():
    user = UserFactory(is_active=False)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(reverse("accounts:me"))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "permission_denied"
