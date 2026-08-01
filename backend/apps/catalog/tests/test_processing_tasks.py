from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.contrib.admin.sites import AdminSite

from apps.catalog.admin import AudioTrackAdmin
from apps.catalog.audio_processing import AudioProcessingError, ProcessedAudio
from apps.catalog.models import (
    AudioProcessingJobStatus,
    AudioProcessingStage,
    AudioTrack,
    TrackProcessingStatus,
)
from apps.catalog.tasks import process_audio_job, queue_audio_processing
from apps.catalog.tests.factories import AudioProcessingJobFactory, AudioTrackFactory

pytestmark = pytest.mark.django_db


def anonymous_admin_request():
    return SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=False,
            is_active=False,
            is_staff=False,
        ),
        request_identifier="",
    )


def test_processing_task_creates_renditions_and_is_idempotent(monkeypatch):
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.QUEUED,
        attempts=1,
        max_attempts=3,
        track__audio_master_file="originals/audio/master.wav",
        track__processing_status=TrackProcessingStatus.PENDING,
    )
    processor = Mock(
        return_value=ProcessedAudio(
            high_name="processed/audio/track/high.mp3",
            low_name="processed/audio/track/low.mp3",
            duration_seconds=125,
            waveform=[0.1, 0.5, 0.2],
        )
    )
    monkeypatch.setattr(
        "apps.catalog.tasks.audio_processing_service.process", processor
    )

    first = process_audio_job(str(job.pk))
    second = process_audio_job(str(job.pk))

    job.refresh_from_db()
    job.track.refresh_from_db()
    assert first == {"claimed": True, "completed": True, "jobId": str(job.pk)}
    assert second == {"claimed": False, "jobId": str(job.pk)}
    assert job.status == AudioProcessingJobStatus.READY
    assert job.stage == AudioProcessingStage.FINALIZING
    assert job.attempts == 2
    assert job.track.processing_status == TrackProcessingStatus.READY
    assert job.track.stream_file_high.name == "processed/audio/track/high.mp3"
    assert job.track.stream_file_low.name == "processed/audio/track/low.mp3"
    assert job.track.duration_seconds == 125
    assert job.track.waveform_data == [0.1, 0.5, 0.2]
    processor.assert_called_once()


def test_processing_task_records_safe_failure(monkeypatch):
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.QUEUED,
        track__audio_master_file="originals/audio/broken.wav",
    )
    monkeypatch.setattr(
        "apps.catalog.tasks.audio_processing_service.process",
        Mock(
            side_effect=AudioProcessingError(
                AudioProcessingStage.TRANSCODING,
                "The audio file could not be processed.",
                "private diagnostic",
            )
        ),
    )

    result = process_audio_job(str(job.pk))

    job.refresh_from_db()
    job.track.refresh_from_db()
    assert result["completed"] is False
    assert job.status == AudioProcessingJobStatus.FAILED
    assert job.stage == AudioProcessingStage.TRANSCODING
    assert job.error_summary == "The audio file could not be processed."
    assert job.technical_error == "private diagnostic"
    assert job.track.processing_status == TrackProcessingStatus.FAILED


@pytest.mark.django_db(transaction=True)
def test_queue_audio_processing_creates_one_job_and_dispatches_once(monkeypatch):
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        audio_master_file="originals/audio/master.wav",
        processing_status=TrackProcessingStatus.READY,
    )
    delay = Mock()
    monkeypatch.setattr("apps.catalog.tasks.process_audio_job.delay", delay)

    first = queue_audio_processing(track)
    first.status = AudioProcessingJobStatus.PROCESSING
    first.save(update_fields=("status", "updated_at"))
    second = queue_audio_processing(track)

    track.refresh_from_db()
    assert first.pk == second.pk
    assert track.processing_status == TrackProcessingStatus.PENDING
    delay.assert_called_once_with(str(first.pk))


def test_audio_track_admin_queues_changed_master(monkeypatch):
    track = AudioTrackFactory(audio_master_file="")
    track.audio_master_file.name = "originals/audio/replacement.wav"
    queue = Mock()
    monkeypatch.setattr("apps.catalog.admin.queue_audio_processing", queue)
    model_admin = AudioTrackAdmin(AudioTrack, AdminSite())

    model_admin.save_model(
        anonymous_admin_request(),
        track,
        Mock(changed_data=["audio_master_file"]),
        change=True,
    )

    queue.assert_called_once_with(track)


def test_audio_track_admin_does_not_queue_metadata_only_change(monkeypatch):
    track = AudioTrackFactory(audio_master_file="originals/audio/master.wav")
    queue = Mock()
    monkeypatch.setattr("apps.catalog.admin.queue_audio_processing", queue)
    model_admin = AudioTrackAdmin(AudioTrack, AdminSite())

    model_admin.save_model(
        anonymous_admin_request(),
        track,
        Mock(changed_data=["title_ne"]),
        change=True,
    )

    queue.assert_not_called()
