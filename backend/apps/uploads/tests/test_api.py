from datetime import timedelta
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.uploads.models import UploadSession, UploadStatus, UploadType

pytestmark = pytest.mark.django_db


@pytest.fixture
def creator():
    return UserFactory(is_creator=True)


@pytest.fixture
def client(creator):
    api_client = APIClient()
    api_client.force_authenticate(creator)
    return api_client


@pytest.fixture(autouse=True)
def s3_settings(settings):
    settings.USE_S3_STORAGE = True
    settings.AWS_S3_AUDIO_BUCKET_NAME = "private-audio"
    settings.AWS_S3_COVER_BUCKET_NAME = "private-covers"
    settings.UPLOAD_SESSION_EXPIRY_SECONDS = 600


def pending_session(user, **kwargs):
    defaults = {
        "user": user,
        "upload_type": UploadType.AUDIO_MASTER,
        "object_key": f"temporary/uploads/audio-master/{user.id}/object.mp3",
        "original_filename": "story.mp3",
        "content_type": "audio/mpeg",
        "expected_size": 1024,
        "expires_at": timezone.now() + timedelta(minutes=10),
    }
    defaults.update(kwargs)
    return UploadSession.objects.create(**defaults)


@patch("apps.uploads.services.get_s3_client")
def test_creator_requests_exact_size_constrained_presigned_upload(
    get_client,
    client,
    creator,
):
    s3 = Mock()
    s3.generate_presigned_post.return_value = {
        "url": "https://private-audio.s3.amazonaws.com/",
        "fields": {"policy": "signed-policy"},
    }
    get_client.return_value = s3

    response = client.post(
        reverse("uploads:request"),
        {
            "uploadType": "audio_master",
            "originalFilename": "../../My Recording.MP3",
            "contentType": "audio/mpeg",
            "expectedSize": 1024,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    session = UploadSession.objects.get()
    assert session.user == creator
    assert session.original_filename == "My Recording.MP3"
    assert session.object_key.startswith(
        f"temporary/uploads/audio-master/{creator.id}/{session.id}/"
    )
    assert "My Recording" not in session.object_key
    assert response.data["upload"]["url"].startswith("https://")
    call = s3.generate_presigned_post.call_args.kwargs
    assert call["Bucket"] == "private-audio"
    assert call["Key"] == session.object_key
    assert ["content-length-range", 1024, 1024 + 1024 * 1024] in call["Conditions"]
    assert {"Content-Type": "audio/mpeg"} in call["Conditions"]
    assert call["Fields"]["x-amz-server-side-encryption"] == "AES256"


@pytest.mark.parametrize(
    ("upload_type", "filename", "content_type", "bucket", "prefix"),
    [
        (
            "cover_image",
            "cover.webp",
            "image/webp",
            "private-covers",
            "covers",
        ),
        (
            "narrator_image",
            "narrator.jpg",
            "image/jpeg",
            "private-covers",
            "narrators",
        ),
        (
            "author_image",
            "author.png",
            "image/png",
            "private-covers",
            "authors",
        ),
    ],
)
@patch("apps.uploads.services.get_s3_client")
def test_image_upload_types_use_private_cover_bucket(
    get_client,
    upload_type,
    filename,
    content_type,
    bucket,
    prefix,
    client,
):
    s3 = Mock()
    s3.generate_presigned_post.return_value = {"url": "https://s3/", "fields": {}}
    get_client.return_value = s3

    response = client.post(
        reverse("uploads:request"),
        {
            "uploadType": upload_type,
            "originalFilename": filename,
            "contentType": content_type,
            "expectedSize": 500,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert s3.generate_presigned_post.call_args.kwargs["Bucket"] == bucket
    assert f"temporary/uploads/{prefix}/" in response.data["objectKey"]


@patch("apps.uploads.services.get_s3_client")
def test_confirm_verifies_object_metadata_before_transition(
    get_client, client, creator
):
    session = pending_session(creator)
    s3 = Mock()
    s3.head_object.return_value = {
        "ContentLength": session.expected_size,
        "ContentType": session.content_type,
        "ServerSideEncryption": "AES256",
    }
    s3.get_object.return_value = {"Body": BytesIO(b"ID3" + b"\x00" * 100)}
    get_client.return_value = s3

    response = client.post(reverse("uploads:confirm", args=[session.id]))

    assert response.status_code == status.HTTP_200_OK
    session.refresh_from_db()
    assert session.status == UploadStatus.CONFIRMED
    assert session.actual_size == session.expected_size
    s3.head_object.assert_called_once_with(
        Bucket="private-audio",
        Key=session.object_key,
    )
    s3.get_object.assert_called_once_with(
        Bucket="private-audio",
        Key=session.object_key,
        Range="bytes=0-4095",
    )

    repeated = client.post(reverse("uploads:confirm", args=[session.id]))
    assert repeated.status_code == status.HTTP_200_OK
    s3.head_object.assert_called_once()


@pytest.mark.parametrize(
    "metadata,field",
    [
        ({"ContentLength": 999, "ContentType": "audio/mpeg"}, "expectedSize"),
        ({"ContentLength": 1024, "ContentType": "application/pdf"}, "contentType"),
    ],
)
@patch("apps.uploads.services.get_s3_client")
def test_confirm_rejects_mismatched_object_metadata(
    get_client,
    metadata,
    field,
    client,
    creator,
):
    session = pending_session(creator)
    s3 = Mock()
    s3.head_object.return_value = metadata
    get_client.return_value = s3

    response = client.post(reverse("uploads:confirm", args=[session.id]))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.data["errors"]
    session.refresh_from_db()
    assert session.status == UploadStatus.PENDING


@patch("apps.uploads.services.get_s3_client")
def test_confirm_rejects_contents_that_do_not_match_declared_type(
    get_client,
    client,
    creator,
):
    session = pending_session(creator)
    s3 = Mock()
    s3.head_object.return_value = {
        "ContentLength": session.expected_size,
        "ContentType": session.content_type,
        "ServerSideEncryption": "AES256",
    }
    s3.get_object.return_value = {
        "Body": BytesIO(b"MZ executable contents"),
    }
    get_client.return_value = s3

    response = client.post(reverse("uploads:confirm", args=[session.id]))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "upload" in response.data["errors"]
    session.refresh_from_db()
    assert session.status == UploadStatus.PENDING


@patch("apps.uploads.services.get_s3_client")
def test_confirm_requires_uploaded_object_to_exist(get_client, client, creator):
    session = pending_session(creator)
    s3 = Mock()
    s3.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "HeadObject",
    )
    get_client.return_value = s3

    response = client.post(reverse("uploads:confirm", args=[session.id]))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "upload" in response.data["errors"]
    session.refresh_from_db()
    assert session.status == UploadStatus.PENDING


@patch("apps.uploads.services.get_s3_client")
def test_cancel_removes_temporary_object_and_is_idempotent(
    get_client,
    client,
    creator,
):
    session = pending_session(creator)
    s3 = Mock()
    get_client.return_value = s3

    response = client.post(reverse("uploads:cancel", args=[session.id]))
    repeated = client.post(reverse("uploads:cancel", args=[session.id]))

    assert response.status_code == status.HTTP_200_OK
    assert repeated.status_code == status.HTTP_200_OK
    assert repeated.data["status"] == UploadStatus.CANCELED
    s3.delete_object.assert_called_once_with(
        Bucket="private-audio",
        Key=session.object_key,
    )


def test_status_expires_pending_session(client, creator):
    session = pending_session(
        creator,
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    response = client.get(reverse("uploads:status", args=[session.id]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == UploadStatus.EXPIRED


def test_expired_session_cannot_be_confirmed_and_remains_expired(client, creator):
    session = pending_session(
        creator,
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    with patch("apps.uploads.services.get_s3_client") as get_client:
        response = client.post(reverse("uploads:confirm", args=[session.id]))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    session.refresh_from_db()
    assert session.status == UploadStatus.EXPIRED
    get_client.assert_not_called()


def test_upload_endpoints_require_creator_or_staff():
    request_url = reverse("uploads:request")
    payload = {
        "uploadType": "audio_master",
        "originalFilename": "story.mp3",
        "contentType": "audio/mpeg",
        "expectedSize": 100,
    }
    anonymous = APIClient().post(request_url, payload, format="json")
    listener_client = APIClient()
    listener_client.force_authenticate(UserFactory(is_creator=False, is_staff=False))
    listener = listener_client.post(request_url, payload, format="json")

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert listener.status_code == status.HTTP_403_FORBIDDEN


@patch("apps.uploads.services.get_s3_client")
def test_staff_can_request_upload_without_creator_flag(get_client):
    s3 = Mock()
    s3.generate_presigned_post.return_value = {"url": "https://s3/", "fields": {}}
    get_client.return_value = s3
    staff_client = APIClient()
    staff_client.force_authenticate(
        UserFactory(is_creator=False, is_staff=True),
    )

    response = staff_client.post(
        reverse("uploads:request"),
        {
            "uploadType": "cover_image",
            "originalFilename": "cover.jpg",
            "contentType": "image/jpeg",
            "expectedSize": 100,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_session_is_visible_only_to_its_owner(client):
    session = pending_session(UserFactory(is_creator=True))

    response = client.get(reverse("uploads:status", args=[session.id]))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "payload,field",
    [
        (
            {
                "uploadType": "audio_master",
                "originalFilename": "story.exe",
                "contentType": "audio/mpeg",
                "expectedSize": 100,
            },
            "originalFilename",
        ),
        (
            {
                "uploadType": "cover_image",
                "originalFilename": "cover.jpg",
                "contentType": "application/pdf",
                "expectedSize": 100,
            },
            "contentType",
        ),
        (
            {
                "uploadType": "cover_image",
                "originalFilename": "cover.jpg",
                "contentType": "image/jpeg",
                "expectedSize": 10_485_761,
            },
            "expectedSize",
        ),
        (
            {
                "uploadType": "cover_image",
                "originalFilename": "cover.jpg",
                "contentType": "image/png",
                "expectedSize": 100,
            },
            "contentType",
        ),
        (
            {
                "uploadType": "cover_image",
                "originalFilename": "bad\u0000name.jpg",
                "contentType": "image/jpeg",
                "expectedSize": 100,
            },
            "originalFilename",
        ),
    ],
)
def test_invalid_file_metadata_is_rejected_before_signing(client, payload, field):
    with patch("apps.uploads.services.get_s3_client") as get_client:
        response = client.post(reverse("uploads:request"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.data["errors"]
    get_client.assert_not_called()
    assert UploadSession.objects.count() == 0
