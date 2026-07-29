import pytest

from apps.catalog.models import (
    AudioProcessingJobStatus,
    TrackProcessingStatus,
)
from apps.catalog.tasks import process_audio_job
from apps.catalog.tests.factories import AudioProcessingJobFactory

pytestmark = pytest.mark.django_db


def test_processing_task_claim_is_idempotent():
    job = AudioProcessingJobFactory(
        status=AudioProcessingJobStatus.QUEUED,
        attempts=1,
        max_attempts=3,
        track__processing_status=TrackProcessingStatus.PENDING,
    )

    first = process_audio_job(str(job.pk))
    second = process_audio_job(str(job.pk))

    job.refresh_from_db()
    job.track.refresh_from_db()
    assert first["claimed"] is True
    assert second["claimed"] is False
    assert job.status == AudioProcessingJobStatus.PROCESSING
    assert job.attempts == 2
    assert job.track.processing_status == TrackProcessingStatus.PROCESSING
