from datetime import timedelta
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.media_access.services import (
    MediaDeliveryUnavailable,
    cloudfront_media_service,
)
from apps.narrators.tests.factories import NarratorFactory
from apps.subscriptions.models import SubscriptionStatus
from apps.subscriptions.tests.factories import UserSubscriptionFactory

pytestmark = pytest.mark.django_db

PRIVATE_FIELDS = {
    "audio_master_file",
    "stream_file_high",
    "stream_file_low",
    "audioMasterFile",
    "streamFileHigh",
    "streamFileLow",
    "introduction_audio_file",
    "introductionAudioFile",
    "introduction_notes",
    "introductionNotes",
}


@pytest.fixture(autouse=True)
def cloudfront_settings(settings):
    settings.CLOUDFRONT_MEDIA_DOMAIN = "audio.example.com"
    settings.CLOUDFRONT_KEY_PAIR_ID = "KTEST"
    settings.CLOUDFRONT_PRIVATE_KEY = "test-key-is-mocked"
    settings.CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS = 300


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@patch("apps.media_access.services.cloudfront_media_service._signed_url")
def test_admin_object_preview_requires_staff_and_uses_short_lived_cloudfront_url(
    signed_url,
):
    signed_url.return_value = "https://audio.example.com/restricted/signed"
    staff = UserFactory(is_staff=True)
    before = timezone.now()

    delivery = cloudfront_media_service.deliver_admin_object(
        object_key="temporary/uploads/audio-master/user/session/object.mp3",
        quality="original",
        user=staff,
    )

    assert delivery["url"].startswith("https://audio.example.com/")
    assert delivery["expiresAt"] > before
    assert delivery["expiresAt"] <= before + timedelta(seconds=301)
    signed_url.assert_called_once()


def test_admin_object_preview_rejects_nonstaff():
    with pytest.raises(PermissionDenied, match="Authorized staff"):
        cloudfront_media_service.deliver_admin_object(
            object_key="temporary/uploads/audio-master/user/session/object.mp3",
            quality="original",
            user=UserFactory(),
        )


@patch("apps.media_access.services.boto3.client")
def test_admin_object_preview_uses_private_s3_when_cloudfront_is_disabled(
    s3_client,
    settings,
):
    settings.CLOUDFRONT_MEDIA_ENABLED = False
    settings.CLOUDFRONT_MEDIA_DOMAIN = ""
    settings.USE_S3_STORAGE = True
    settings.AWS_S3_AUDIO_BUCKET_NAME = "private-audio"
    s3_client.return_value.generate_presigned_url.return_value = (
        "https://private-audio.s3.amazonaws.com/temporary/upload.mp3"
        "?X-Amz-Signature=signed"
    )

    delivery = cloudfront_media_service.deliver_admin_object(
        object_key="temporary/uploads/audio-master/user/session/object.mp3",
        quality="original",
        user=UserFactory(is_staff=True),
    )

    assert "X-Amz-Signature=signed" in delivery["url"]
    assert delivery["expiresAt"] is not None


def test_signed_media_lifetime_is_enforced_inside_delivery_service(settings):
    settings.CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS = 3600

    with pytest.raises(MediaDeliveryUnavailable, match="lifetime"):
        cloudfront_media_service._signed_expiration()


def test_admin_object_preview_rejects_non_audio_or_traversal_keys():
    staff = UserFactory(is_staff=True)

    with pytest.raises(ValidationError, match="object key is invalid"):
        cloudfront_media_service.deliver_admin_object(
            object_key="temporary/uploads/covers/user/cover.jpg",
            quality="original",
            user=staff,
        )
    with pytest.raises(ValidationError, match="object key is invalid"):
        cloudfront_media_service.deliver_admin_object(
            object_key="temporary/uploads/audio-master/../secret.mp3",
            quality="original",
            user=staff,
        )


@patch("apps.media_access.services.cloudfront_media_service._signed_url")
def test_admin_document_delivery_uses_private_cloudfront_and_permission(
    signed_url,
):
    signed_url.return_value = (
        "https://media.example.com/restricted/document.pdf?Signature=signed"
    )
    user = UserFactory(is_staff=True)
    permission = Permission.objects.get(
        content_type__app_label="catalog",
        codename="view_permissiondocument",
    )
    user.user_permissions.add(permission)
    user = user.__class__.objects.get(pk=user.pk)

    delivery = cloudfront_media_service.deliver_admin_document(
        object_key=(
            "originals/permission-documents/permissiondocument/id/document.pdf"
        ),
        user=user,
    )

    assert delivery["url"] == signed_url.return_value
    resource_url = signed_url.call_args.args[0]
    assert resource_url.startswith("https://")
    assert "/restricted/originals/permission-documents/" in resource_url
    assert "s3" not in resource_url


def test_admin_document_delivery_rejects_unauthorized_staff_and_unsafe_keys():
    unauthorized = UserFactory(is_staff=True)
    with pytest.raises(PermissionDenied):
        cloudfront_media_service.deliver_admin_document(
            object_key="originals/permission-documents/document.pdf",
            user=unauthorized,
        )

    authorized = UserFactory(is_staff=True, is_superuser=True)
    with pytest.raises(ValidationError):
        cloudfront_media_service.deliver_admin_document(
            object_key="../permission-documents/document.pdf",
            user=authorized,
        )


def entitlement(user, *, starts_at=None, expires_at=None, is_revoked=False):
    now = timezone.now()
    status = SubscriptionStatus.CANCELED if is_revoked else SubscriptionStatus.ACTIVE
    return UserSubscriptionFactory(
        user=user,
        starts_at=starts_at or now - timedelta(days=1),
        ends_at=expires_at or now + timedelta(days=1),
        status=status,
    )


def test_anonymous_free_track_receives_stable_cloudfront_url():
    track = AudioTrackFactory(
        is_premium=False,
        stream_file_high="processed/audio/track/high.mp3",
        stream_file_low="processed/audio/track/low.mp3",
    )

    first = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "auto"},
    )
    second = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "high"},
    )

    assert first.status_code == status.HTTP_200_OK
    assert first.data["quality"] == "high"
    assert first.data["url"] == second.data["url"]
    assert first.data["url"].startswith("https://audio.example.com/free/")
    assert "amazonaws.com" not in first.data["url"]
    assert first.data["expiresAt"] is None
    assert first.data["authorization"] == {
        "status": "authorized",
        "accessType": "free",
        "isEntitled": False,
        "isPrivileged": False,
    }
    assert first.data["track"]["id"] == str(track.id)
    assert PRIVATE_FIELDS.isdisjoint(first.data["track"])
    assert first.data["introduction"] is None


def test_introduction_is_returned_only_when_sequenced_playback_requests_it():
    track = AudioTrackFactory(
        stream_file_high="processed/audio/track/high.mp3",
        introduction_audio_file="processed/audio/track/introduction.mp3",
        introduction_duration_seconds=14,
        introduction_enabled=True,
    )
    url = reverse("catalog:track-stream", kwargs={"slug": track.slug})

    direct = APIClient().get(url)
    sequenced = APIClient().get(url, {"includeIntroduction": "true"})

    assert direct.status_code == status.HTTP_200_OK
    assert direct.data["introduction"] is None
    assert sequenced.status_code == status.HTTP_200_OK
    assert sequenced.data["introduction"] == {
        "url": (
            "https://audio.example.com/free/processed/audio/track/introduction.mp3"
        ),
        "expiresAt": None,
        "duration": 14,
    }


def test_disabled_or_missing_introduction_is_not_returned():
    track = AudioTrackFactory(
        stream_file_high="processed/audio/track/high.mp3",
        introduction_audio_file="processed/audio/track/introduction.mp3",
        introduction_enabled=False,
    )

    response = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"includeIntroduction": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["introduction"] is None


@patch("apps.media_access.services.boto3.client")
def test_disabled_cloudfront_uses_short_lived_private_s3_url(s3_client, settings):
    settings.CLOUDFRONT_MEDIA_ENABLED = False
    settings.CLOUDFRONT_MEDIA_DOMAIN = ""
    settings.USE_S3_STORAGE = True
    settings.AWS_S3_AUDIO_BUCKET_NAME = "private-audio"
    settings.AWS_S3_REGION_NAME = "ap-south-1"
    settings.AWS_S3_ENDPOINT_URL = None
    s3_client.return_value.generate_presigned_url.return_value = (
        "https://private-audio.s3.amazonaws.com/processed/audio/track/high.mp3"
        "?X-Amz-Signature=signed"
    )
    track = AudioTrackFactory(
        is_premium=False,
        stream_file_high="processed/audio/track/high.mp3",
    )

    response = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "high"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "X-Amz-Signature=signed" in response.data["url"]
    assert response.data["expiresAt"] is not None
    s3_client.return_value.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={
            "Bucket": "private-audio",
            "Key": "processed/audio/track/high.mp3",
        },
        ExpiresIn=300,
    )


def test_anonymous_cannot_stream_premium_track():
    track = AudioTrackFactory(
        is_premium=True,
        stream_file_low="processed/audio/track/low.mp3",
    )

    response = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "low"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "url" not in response.data


@patch("apps.media_access.services.cloudfront_media_service._signed_url")
def test_active_entitlement_receives_short_lived_signed_premium_url(
    signed_url,
):
    signed_url.return_value = (
        "https://audio.example.com/media.mp3?Expires=1&Signature=x&Key-Pair-Id=KTEST"
    )
    user = UserFactory()
    entitlement(user)
    track = AudioTrackFactory(
        is_premium=True,
        stream_file_high="processed/audio/track/high.mp3",
    )
    before = timezone.now()

    response = authenticated_client(user).get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "high"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "Signature=" in response.data["url"]
    expires_at = parse_datetime(response.data["expiresAt"])
    assert before + timedelta(seconds=295) <= expires_at
    assert expires_at <= timezone.now() + timedelta(seconds=305)
    assert response.data["authorization"]["accessType"] == "active"
    assert response.data["authorization"]["isEntitled"] is True
    signed_url.assert_called_once()


@pytest.mark.parametrize(
    "entitlement_kwargs",
    [
        {"expires_at": timezone.now() - timedelta(seconds=1)},
        {"is_revoked": True},
        {"starts_at": timezone.now() + timedelta(hours=1)},
    ],
)
def test_inactive_or_expired_entitlement_is_denied(entitlement_kwargs):
    user = UserFactory()
    starts_at = entitlement_kwargs.get(
        "starts_at",
        timezone.now() - timedelta(days=2),
    )
    expires_at = entitlement_kwargs.get(
        "expires_at",
        timezone.now() + timedelta(days=2),
    )
    entitlement(
        user,
        starts_at=starts_at,
        expires_at=expires_at,
        is_revoked=entitlement_kwargs.get("is_revoked", False),
    )
    track = AudioTrackFactory(
        is_premium=True,
        stream_file_low="processed/audio/track/low.mp3",
    )

    response = authenticated_client(user).get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "low"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_unpublished_track_is_concealed_from_anonymous_users():
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        stream_file_low="processed/audio/track/low.mp3",
    )

    response = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("role", ["staff", "creator"])
@patch("apps.media_access.services.cloudfront_media_service._signed_url")
def test_authorized_staff_or_linked_creator_can_stream_unpublished_track(
    signed_url,
    role,
):
    signed_url.return_value = "https://audio.example.com/draft?Signature=x"
    if role == "staff":
        user = UserFactory(is_staff=True)
        narrator = NarratorFactory()
    else:
        user = UserFactory(is_creator=True)
        narrator = NarratorFactory(user=user)
    track = AudioTrackFactory(
        narrator=narrator,
        is_published=False,
        published_at=None,
        stream_file_low="processed/audio/track/low.mp3",
    )

    response = authenticated_client(user).get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "low"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["expiresAt"] is not None
    assert response.data["authorization"]["accessType"] == role
    assert response.data["authorization"]["isPrivileged"] is True


def test_unlinked_creator_cannot_stream_unpublished_track():
    creator = UserFactory(is_creator=True)
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        stream_file_low="processed/audio/track/low.mp3",
    )

    response = authenticated_client(creator).get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_requested_quality_must_exist():
    track = AudioTrackFactory(
        stream_file_high="",
        stream_file_low="processed/audio/track/low.mp3",
    )

    unavailable = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "high"},
    )
    automatic = APIClient().get(
        reverse("catalog:track-stream", kwargs={"slug": track.slug}),
        {"quality": "auto"},
    )

    assert unavailable.status_code == status.HTTP_400_BAD_REQUEST
    assert automatic.status_code == status.HTTP_200_OK
    assert automatic.data["quality"] == "low"


def test_cloudfront_signer_generates_canned_policy_parameters(settings):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings.CLOUDFRONT_PRIVATE_KEY = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    url = cloudfront_media_service._signed_url(
        "https://audio.example.com/premium/media.mp3",
        timezone.now() + timedelta(minutes=5),
    )

    assert "Expires=" in url
    assert "Signature=" in url
    assert "Key-Pair-Id=KTEST" in url
