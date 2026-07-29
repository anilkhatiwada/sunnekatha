from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.common.admin_status import ProcessingState
from apps.uploads.admin import (
    UploadExpiryFilter,
    UploadProcessingStateFilter,
    UploadSessionAdmin,
    human_file_size,
)
from apps.uploads.models import UploadSession, UploadStatus, UploadType

pytestmark = pytest.mark.django_db


def audio_upload(user, **kwargs):
    defaults = {
        "user": user,
        "upload_type": UploadType.AUDIO_MASTER,
        "object_key": f"temporary/uploads/audio-master/{user.pk}/object.mp3",
        "original_filename": "story.mp3",
        "content_type": "audio/mpeg",
        "expected_size": 1024,
        "status": UploadStatus.CONFIRMED,
        "expires_at": timezone.now() + timedelta(minutes=10),
    }
    defaults.update(kwargs)
    return UploadSession.objects.create(**defaults)


def test_upload_admin_uses_reusable_secure_audio_widget():
    model_admin = admin.site._registry[UploadSession]

    assert isinstance(model_admin, UploadSessionAdmin)
    assert "audio_preview" in model_admin.readonly_fields
    assert "admin/js/secure-audio-preview.js" in model_admin.media._js
    assert UploadProcessingStateFilter in model_admin.list_filter
    assert UploadExpiryFilter in model_admin.list_filter
    assert "object_key" in model_admin.exclude
    assert "object_key" not in model_admin.search_fields
    assert tuple(
        value for value, _ in UploadProcessingStateFilter.lookups(None, None, None)
    ) == tuple(value for value, _ in ProcessingState.CHOICES)


def test_upload_admin_displays_human_readable_expected_and_actual_sizes():
    model_admin = admin.site._registry[UploadSession]
    upload = audio_upload(
        UserFactory(),
        expected_size=5 * 1024 * 1024,
        actual_size=5 * 1024 * 1024,
    )

    assert human_file_size(1536) == "1.5 KB"
    assert model_admin.expected_size_display(upload) == "5.0 MB"
    assert model_admin.actual_size_display(upload) == "5.0 MB"


def test_confirmed_audio_upload_renders_widget_without_signing(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    upload = audio_upload(user)
    deliver = Mock()
    monkeypatch.setattr(
        "apps.uploads.admin.cloudfront_media_service.deliver_admin_object",
        deliver,
    )
    client.force_login(user)

    response = client.get(
        reverse("admin:uploads_uploadsession_change", args=(upload.pk,))
    )

    assert response.status_code == 200
    assert b"Original upload: available" in response.content
    assert b"Low quality: unavailable" in response.content
    assert b"High quality: unavailable" in response.content
    deliver.assert_not_called()


def test_upload_list_and_detail_use_consistent_uploaded_badge(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    upload = audio_upload(user)
    client.force_login(user)

    listing = client.get(reverse("admin:uploads_uploadsession_changelist"))
    detail = client.get(
        reverse("admin:uploads_uploadsession_change", args=(upload.pk,))
    )

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert b"Uploaded" in listing.content
    assert b"cloud_done" in listing.content
    assert b"Uploaded" in detail.content


def test_upload_preview_delegates_to_staff_only_cloudfront_service(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    upload = audio_upload(user)
    deliver = Mock(
        return_value={
            "quality": "original",
            "url": "https://audio.example.com/restricted/signed",
            "expiresAt": None,
        }
    )
    monkeypatch.setattr(
        "apps.uploads.admin.cloudfront_media_service.deliver_admin_object",
        deliver,
    )
    client.force_login(user)
    url = reverse(
        "admin:uploads_uploadsession_audio_delivery",
        kwargs={"object_id": upload.pk, "quality": "original"},
    )

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()["url"].startswith("https://audio.example.com/")
    deliver.assert_called_once_with(
        object_key=upload.object_key,
        quality="original",
        user=user,
    )


def test_non_audio_upload_has_graceful_unavailable_widget(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    upload = audio_upload(
        user,
        upload_type=UploadType.COVER_IMAGE,
        object_key=f"temporary/uploads/covers/{user.pk}/cover.jpg",
        original_filename="cover.jpg",
        content_type="image/jpeg",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.uploads.admin.cloudfront_media_service.deliver_admin_object",
        deliver,
    )
    client.force_login(user)

    response = client.get(
        reverse("admin:uploads_uploadsession_change", args=(upload.pk,))
    )

    assert response.status_code == 200
    assert b"No playable audio is available" in response.content
    deliver.assert_not_called()


def test_cancel_admin_action_requires_confirmation(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    upload = audio_upload(user, status=UploadStatus.PENDING)
    cancel = Mock()
    monkeypatch.setattr("apps.uploads.admin.upload_session_service.cancel", cancel)
    client.force_login(user)
    url = reverse("admin:uploads_uploadsession_changelist")

    response = client.post(
        url,
        {
            "action": "cancel_uploads",
            "_selected_action": str(upload.pk),
        },
    )

    assert response.status_code == 200
    assert b"Confirm upload cancellation" in response.content
    cancel.assert_not_called()


def test_temporary_object_delete_action_requires_delete_permission(rf):
    model_admin = admin.site._registry[UploadSession]
    editor = UserFactory(is_staff=True)
    editor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="uploads",
            codename="change_uploadsession",
        )
    )
    request = rf.get("/")
    request.user = editor

    assert "delete_temporary_objects" not in model_admin.get_actions(request)

    editor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="uploads",
            codename="delete_uploadsession",
        )
    )
    editor = editor.__class__.objects.get(pk=editor.pk)
    request.user = editor
    assert "delete_temporary_objects" in model_admin.get_actions(request)
