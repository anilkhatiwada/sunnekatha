from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import SocialIdentity, User
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def google_payload(**overrides):
    payload = {
        "sub": "google-subject-1",
        "email": "listener@gmail.com",
        "email_verified": True,
        "name": "Google Listener",
    }
    payload.update(overrides)
    return payload


@patch("apps.accounts.views.verify_google_credential")
def test_google_login_creates_linked_user_and_returns_jwt(verify):
    verify.return_value = google_payload()

    response = APIClient().post(
        reverse("accounts:google"),
        {"credential": "google-id-token"},
        format="json",
        HTTP_X_SUNNEKATHA_AUTH="google",
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data) == {"access", "refresh", "user"}
    user = User.objects.get(email="listener@gmail.com")
    assert not user.has_usable_password()
    assert SocialIdentity.objects.filter(user=user, subject="google-subject-1").exists()


@patch("apps.accounts.views.verify_google_credential")
def test_google_login_reuses_subject_identity(verify):
    verify.return_value = google_payload()
    client = APIClient()

    first = client.post(
        reverse("accounts:google"),
        {"credential": "first"},
        format="json",
        HTTP_X_SUNNEKATHA_AUTH="google",
    )
    second = client.post(
        reverse("accounts:google"),
        {"credential": "second"},
        format="json",
        HTTP_X_SUNNEKATHA_AUTH="google",
    )

    assert first.status_code == second.status_code == status.HTTP_200_OK
    assert User.objects.count() == 1
    assert SocialIdentity.objects.count() == 1


@patch("apps.accounts.views.verify_google_credential")
def test_google_login_does_not_auto_link_non_authoritative_existing_email(verify):
    UserFactory(email="listener@example.com")
    verify.return_value = google_payload(
        email="listener@example.com",
        hd=None,
    )

    response = APIClient().post(
        reverse("accounts:google"),
        {"credential": "google-id-token"},
        format="json",
        HTTP_X_SUNNEKATHA_AUTH="google",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert SocialIdentity.objects.count() == 0
