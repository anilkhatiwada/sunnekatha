from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    AudioProcessingJob,
    AudioProcessingJobStatus,
    TrackProcessingStatus,
)


@shared_task
def process_audio_job(job_id):
    """Claim one queued audio job for the processing worker.

    Actual media transformation remains behind the audio-processing boundary.
    The claim is deliberately idempotent so duplicate broker delivery cannot
    start the same database job twice.
    """
    with transaction.atomic():
        job = (
            AudioProcessingJob.objects.select_for_update()
            .select_related("track")
            .filter(pk=job_id)
            .first()
        )
        if (
            job is None
            or job.status != AudioProcessingJobStatus.QUEUED
            or job.attempts >= job.max_attempts
        ):
            return {"claimed": False, "jobId": str(job_id)}

        now = timezone.now()
        job.status = AudioProcessingJobStatus.PROCESSING
        job.attempts += 1
        job.last_attempt_at = now
        job.save(
            update_fields=(
                "status",
                "attempts",
                "last_attempt_at",
                "updated_at",
            )
        )
        job.track.processing_status = TrackProcessingStatus.PROCESSING
        job.track.save(update_fields=("processing_status", "updated_at"))
        return {"claimed": True, "jobId": str(job.pk)}
