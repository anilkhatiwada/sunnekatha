from datetime import timedelta

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import (
    AudioProcessingJobAdmin,
    ProcessingJobStateFilter,
    TrackProcessingStateFilter,
)
from apps.catalog.models import (
    AudioProcessingJob,
    AudioProcessingJobStatus,
    AudioProcessingStage,
    TrackProcessingStatus,
)
from apps.catalog.tests.factories import (
    AudioProcessingJobFactory,
    AudioTrackFactory,
)
from apps.common.admin_status import (
    ProcessingState,
    processing_state_badge,
    track_processing_state,
)
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction
from apps.uploads.models import UploadSession, UploadStatus, UploadType

pytestmark = pytest.mark.django_db


def upload_for(user):
    return UploadSession.objects.create(
        user=user,
        upload_type=UploadType.AUDIO_MASTER,
        object_key=f"temporary/uploads/audio-master/{user.pk}/source.mp3",
        original_filename="source.mp3",
        content_type="audio/mpeg",
        expected_size=1024,
        status=UploadStatus.CONFIRMED,
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def test_shared_badges_include_consistent_label_and_material_icon():
    badge = str(processing_state_badge(ProcessingState.FAILED))

    assert "Failed" in badge
    assert "error" in badge
    assert "sk-processing-badge--danger" in badge


def test_track_states_cover_the_seven_editorial_processing_states():
    draft = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PENDING,
        audio_master_file="",
    )
    uploaded = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PENDING,
        audio_master_file="originals/audio/source.mp3",
    )
    queued = AudioProcessingJobFactory().track
    processing = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.PROCESSING,
        track__processing_status=TrackProcessingStatus.PROCESSING,
    ).track
    ready = AudioTrackFactory(is_published=False, published_at=None)
    failed = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        track__processing_status=TrackProcessingStatus.FAILED,
    ).track
    published = AudioTrackFactory()

    assert [
        track_processing_state(track)
        for track in (
            draft,
            uploaded,
            queued,
            processing,
            ready,
            failed,
            published,
        )
    ] == [
        ProcessingState.DRAFT,
        ProcessingState.UPLOADED,
        ProcessingState.QUEUED,
        ProcessingState.PROCESSING,
        ProcessingState.READY,
        ProcessingState.FAILED,
        ProcessingState.PUBLISHED,
    ]


def test_processing_filters_offer_every_state():
    expected = tuple(value for value, _ in ProcessingState.CHOICES)

    assert (
        tuple(
            value for value, _ in TrackProcessingStateFilter.lookups(None, None, None)
        )
        == expected
    )
    assert (
        tuple(value for value, _ in ProcessingJobStateFilter.lookups(None, None, None))
        == expected
    )


def test_failed_job_exposes_editorial_diagnostics_and_relationships():
    uploader = UserFactory()
    upload = upload_for(uploader)
    job = AudioProcessingJobFactory(
        upload_session=upload,
        status=AudioProcessingJobStatus.FAILED,
        stage=AudioProcessingStage.TRANSCODING,
        error_summary="The high-quality rendition could not be generated.",
        technical_error="Traceback: secret internal path",
        attempts=2,
        max_attempts=3,
        last_attempt_at=timezone.now(),
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    model_admin = admin.site._registry[AudioProcessingJob]

    assert isinstance(model_admin, AudioProcessingJobAdmin)
    assert model_admin.attempts_display(job) == "2 / 3"
    assert model_admin.retry_display(job) is True
    assert "Audio transcoding" in job.get_stage_display()
    assert str(job.track.pk) in str(model_admin.track_link(job))
    assert str(upload.pk) in str(model_admin.upload_link(job))


def test_ordinary_editor_cannot_see_technical_error_but_superuser_can(client):
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        error_summary="Safe editor-facing summary.",
        technical_error="SENSITIVE TRACEBACK /private/worker/path",
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    editor = UserFactory(is_staff=True)
    editor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="catalog",
            codename="view_audioprocessingjob",
        )
    )
    client.force_login(editor)
    url = reverse("admin:catalog_audioprocessingjob_change", args=(job.pk,))

    editor_response = client.get(url)

    assert editor_response.status_code == 200
    assert b"Safe editor-facing summary" in editor_response.content
    assert b"SENSITIVE TRACEBACK" not in editor_response.content

    superuser = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(superuser)
    superuser_response = client.get(url)

    assert superuser_response.status_code == 200
    assert b"SENSITIVE TRACEBACK" in superuser_response.content
    assert b"Technical information" in superuser_response.content


def test_failed_processing_page_filters_jobs_and_shows_all_failure_columns(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    failed = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        stage=AudioProcessingStage.WAVEFORM,
        error_summary="Waveform extraction failed.",
        attempts=3,
        max_attempts=3,
        last_attempt_at=timezone.now(),
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    AudioProcessingJobFactory(status=AudioProcessingJobStatus.QUEUED)
    client.force_login(user)

    response = client.get(
        reverse("admin:catalog_audioprocessingjob_changelist"),
        {"processing_state": ProcessingState.FAILED},
    )

    assert response.status_code == 200
    assert failed in response.context["cl"].result_list
    assert len(response.context["cl"].result_list) == 1
    assert b"Error summary" in response.content
    assert b"Attempts" in response.content
    assert b"Last attempt at" in response.content
    assert b"Retry available" in response.content


def test_custom_failed_page_requires_model_permission(client):
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    user = UserFactory(is_staff=True)
    client.force_login(user)
    url = reverse("admin:catalog_audioprocessingjob_failed")

    denied = client.get(url)

    assert denied.status_code == 403

    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="catalog",
            codename="view_audioprocessingjob",
        )
    )
    allowed = client.get(url)

    assert allowed.status_code == 200
    assert job.track.title_ne.encode() in allowed.content
    for label in (
        b"Track title or filename",
        b"Failed processing stage",
        b"Created date",
        b"Upload creator",
    ):
        assert label in allowed.content
    assert allowed.content.count(b"<h1") == 1


def test_view_only_editor_cannot_retry_failed_job(client):
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="catalog",
            codename="view_audioprocessingjob",
        )
    )
    client.force_login(user)

    response = client.post(
        reverse("admin:catalog_audioprocessingjob_retry", args=(job.pk,))
    )

    assert response.status_code == 403
    job.refresh_from_db()
    assert job.status == AudioProcessingJobStatus.FAILED


def test_bulk_retry_requires_confirmation_and_records_actor(
    client, django_capture_on_commit_callbacks, monkeypatch
):
    actor = UserFactory(is_staff=True)
    actor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=(
                "view_audioprocessingjob",
                "retry_audioprocessingjob",
            ),
        )
    )
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        attempts=1,
        max_attempts=3,
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    dispatched = []
    monkeypatch.setattr(
        "apps.catalog.tasks.process_audio_job.delay",
        lambda job_id: dispatched.append(job_id),
    )
    client.force_login(actor)
    url = reverse("admin:catalog_audioprocessingjob_failed")

    confirmation = client.post(url, {"_selected_action": str(job.pk)})

    assert confirmation.status_code == 200
    assert b"Confirm processing retries" in confirmation.content
    job.refresh_from_db()
    assert job.status == AudioProcessingJobStatus.FAILED

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            url,
            {"_selected_action": str(job.pk), "confirm": "yes"},
        )

    assert response.status_code == 302
    job.refresh_from_db()
    assert job.status == AudioProcessingJobStatus.QUEUED
    assert job.retry_initiated_by == actor
    assert job.retry_requested_at is not None
    assert dispatched == [str(job.pk)]
    assert AdministrativeAudit.objects.filter(
        action=AdministrativeAuditAction.PROCESSING_RETRIED,
        object_id=str(job.track_id),
        staff_user=actor,
    ).exists()


def test_repeated_retry_does_not_dispatch_duplicate_active_job(
    client, django_capture_on_commit_callbacks, monkeypatch
):
    actor = UserFactory(is_staff=True)
    actor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=(
                "view_audioprocessingjob",
                "retry_audioprocessingjob",
            ),
        )
    )
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.FAILED,
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    dispatched = []
    monkeypatch.setattr(
        "apps.catalog.tasks.process_audio_job.delay",
        lambda job_id: dispatched.append(job_id),
    )
    client.force_login(actor)
    retry_url = reverse("admin:catalog_audioprocessingjob_retry", args=(job.pk,))

    with django_capture_on_commit_callbacks(execute=True):
        first = client.post(retry_url)
    with django_capture_on_commit_callbacks(execute=True):
        second = client.post(retry_url)

    assert first.status_code == 302
    assert second.status_code == 302
    assert dispatched == [str(job.pk)]
