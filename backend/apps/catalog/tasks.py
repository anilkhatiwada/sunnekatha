import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.catalog.audio_processing import (
    AudioProcessingError,
    audio_processing_service,
)
from apps.catalog.models import (
    AudioProcessingJob,
    AudioProcessingJobStatus,
    AudioProcessingStage,
    AudioTrack,
    TrackProcessingStatus,
)
from apps.common.cache import public_cache_invalidation
from apps.notifications.services import notification_service

logger = logging.getLogger(__name__)


def queue_audio_processing(track, *, upload_session=None):
    """Create or reset one non-active job and enqueue it after commit."""
    if not track.audio_master_file:
        return None
    with transaction.atomic():
        job, created = AudioProcessingJob.objects.select_for_update().get_or_create(
            track=track,
            defaults={
                "upload_session": upload_session,
                "status": AudioProcessingJobStatus.QUEUED,
            },
        )
        if not created and job.status == AudioProcessingJobStatus.PROCESSING:
            return job
        job.upload_session = upload_session or job.upload_session
        job.status = AudioProcessingJobStatus.QUEUED
        job.stage = AudioProcessingStage.UPLOAD
        job.error_summary = ""
        job.technical_error = ""
        job.save()
        AudioTrack.objects.filter(pk=track.pk).update(
            processing_status=TrackProcessingStatus.PENDING,
            updated_at=timezone.now(),
        )
        transaction.on_commit(lambda: process_audio_job.delay(str(job.pk)))
        return job


@shared_task
def process_audio_job(job_id):
    """Idempotently transcode one private master into player renditions."""
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
        job.stage = AudioProcessingStage.UPLOAD
        job.attempts += 1
        job.last_attempt_at = now
        job.save()
        job.track.processing_status = TrackProcessingStatus.PROCESSING
        job.track.save(update_fields=("processing_status", "updated_at"))
        track_id = job.track_id

    result = None
    try:
        track = AudioTrack.objects.get(pk=track_id)
        result = audio_processing_service.process(track)
        with transaction.atomic():
            job = (
                AudioProcessingJob.objects.select_for_update()
                .select_related("track")
                .get(pk=job_id)
            )
            if job.status != AudioProcessingJobStatus.PROCESSING:
                return {"claimed": True, "completed": False, "jobId": str(job_id)}
            old_names = (
                job.track.stream_file_high.name,
                job.track.stream_file_low.name,
            )
            job.track.stream_file_high.name = result.high_name
            job.track.stream_file_low.name = result.low_name
            job.track.duration_seconds = result.duration_seconds
            job.track.waveform_data = result.waveform
            job.track.processing_status = TrackProcessingStatus.READY
            job.track.save(
                update_fields=(
                    "stream_file_high",
                    "stream_file_low",
                    "duration_seconds",
                    "waveform_data",
                    "processing_status",
                    "updated_at",
                )
            )
            job.status = AudioProcessingJobStatus.READY
            job.stage = AudioProcessingStage.FINALIZING
            job.error_summary = ""
            job.technical_error = ""
            job.save()
            upload_session = job.upload_session
            storage = job.track.stream_file_high.storage
            transaction.on_commit(lambda: _delete_files_safely(storage, old_names))
        if upload_session:
            try:
                notification_service.upload_processing_completed(
                    upload_session,
                    track=track,
                )
            except Exception:
                logger.exception("Unable to create audio-processing notification")
        try:
            public_cache_invalidation.for_model(AudioTrack)
        except Exception:
            logger.exception("Unable to invalidate track cache after processing")
        return {"claimed": True, "completed": True, "jobId": str(job_id)}
    except AudioProcessingError as exc:
        return _mark_processing_failed(job_id, exc)
    except Exception as exc:
        if result is not None:
            _delete_files_safely(
                AudioTrack._meta.get_field("stream_file_high").storage,
                (result.high_name, result.low_name),
            )
        error = AudioProcessingError(
            AudioProcessingStage.FINALIZING,
            "Audio processing could not be completed.",
            str(exc),
        )
        return _mark_processing_failed(job_id, error)


def _mark_processing_failed(job_id, error):
    """Persist a safe editor-facing failure while retaining technical detail."""
    with transaction.atomic():
        job = (
            AudioProcessingJob.objects.select_for_update()
            .select_related("track")
            .get(pk=job_id)
        )
        job.status = AudioProcessingJobStatus.FAILED
        job.stage = error.stage
        job.error_summary = error.summary[:500]
        job.technical_error = error.technical[-4000:]
        job.save()
        job.track.processing_status = TrackProcessingStatus.FAILED
        job.track.save(update_fields=("processing_status", "updated_at"))
        upload_session = job.upload_session
    if upload_session:
        try:
            notification_service.upload_processing_failed(upload_session)
        except Exception:
            logger.exception("Unable to create audio-processing failure notification")
    return {"claimed": True, "completed": False, "jobId": str(job_id)}


def _delete_files_safely(storage, names):
    for name in names:
        if not name:
            continue
        try:
            storage.delete(name)
        except Exception:
            logger.exception("Unable to remove replaced audio rendition")
