from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.tests.factories import UserFactory
from apps.uploads.models import UploadSession, UploadStatus, UploadType
from apps.uploads.services import upload_session_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def storage_settings(settings):
    settings.USE_S3_STORAGE = True
    settings.AWS_S3_AUDIO_BUCKET_NAME = "private-audio"


def upload(status):
    user = UserFactory(is_creator=True)
    return UploadSession.objects.create(
        user=user,
        upload_type=UploadType.AUDIO_MASTER,
        object_key=f"temporary/uploads/audio-master/{user.pk}/safe.mp3",
        original_filename="safe.mp3",
        content_type="audio/mpeg",
        expected_size=1024,
        status=status,
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def test_mark_abandoned_uses_valid_state_transition_without_storage_access(
    monkeypatch,
):
    session = upload(UploadStatus.PENDING)
    get_client = Mock()
    monkeypatch.setattr("apps.uploads.services.get_s3_client", get_client)

    upload_session_service.mark_abandoned(session=session, actor=session.user)

    session.refresh_from_db()
    assert session.status == UploadStatus.ABANDONED
    get_client.assert_not_called()


def test_temporary_delete_rejects_active_upload_and_does_not_touch_s3(
    monkeypatch,
):
    session = upload(UploadStatus.PENDING)
    get_client = Mock()
    monkeypatch.setattr("apps.uploads.services.get_s3_client", get_client)

    with pytest.raises(ValidationError):
        upload_session_service.delete_temporary_object(
            session=session,
            actor=session.user,
        )

    get_client.assert_not_called()


def test_temporary_delete_uses_service_owned_bucket_and_key_once(monkeypatch):
    session = upload(UploadStatus.ABANDONED)
    s3 = Mock()
    get_client = Mock(return_value=s3)
    monkeypatch.setattr("apps.uploads.services.get_s3_client", get_client)

    upload_session_service.delete_temporary_object(session=session, actor=session.user)
    upload_session_service.delete_temporary_object(session=session, actor=session.user)

    session.refresh_from_db()
    assert session.temporary_object_deleted_at is not None
    s3.delete_object.assert_called_once_with(
        Bucket="private-audio",
        Key=session.object_key,
    )


def test_upload_service_rejects_non_owner_without_admin_permission():
    session = upload(UploadStatus.PENDING)

    with pytest.raises(PermissionDenied):
        upload_session_service.mark_abandoned(
            session=session,
            actor=UserFactory(is_creator=True),
        )
