from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import (
    Album,
    AudioProcessingJob,
    AudioProcessingJobStatus,
    LiteraryWork,
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.common.audit import administrative_audit_service
from apps.common.cache import public_cache_invalidation
from apps.common.models import AdministrativeAuditAction
from apps.notifications.services import notification_service
from apps.playlists.models import Playlist, PlaylistType


@dataclass(frozen=True)
class EditorialResult:
    updated: int
    skipped: int = 0


class EditorialService:
    """Transactional state transitions used by admin and creator APIs."""

    @staticmethod
    def _require(actor, permission):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm(permission)
        ):
            raise PermissionDenied("Editorial service permission is required.")

    @staticmethod
    @transaction.atomic
    def publish_works(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.change_literarywork")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(is_published=False)
        updated = eligible.update(is_published=True, published_at=now, updated_at=now)
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def unpublish_works(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.change_literarywork")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(is_published=True)
        updated = eligible.update(is_published=False, published_at=None, updated_at=now)
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def duplicate_work(work: LiteraryWork, *, actor) -> LiteraryWork:
        """Create an unpublished editorial copy without copying related tracks."""
        EditorialService._require(actor, "catalog.change_literarywork")
        duplicate = LiteraryWork.objects.create(
            title_ne=work.title_ne,
            title_en=work.title_en,
            subtitle_ne=work.subtitle_ne,
            subtitle_en=work.subtitle_en,
            description_ne=work.description_ne,
            description_en=work.description_en,
            content_type=work.content_type,
            author=work.author,
            language=work.language,
            publication_year=work.publication_year,
            copyright_status=work.copyright_status,
            copyright_owner=work.copyright_owner,
            license_notes=work.license_notes,
            cover_image=work.cover_image,
            is_featured=False,
            is_published=False,
            published_at=None,
        )
        duplicate.genres.set(work.genres.all())
        duplicate.moods.set(work.moods.all())
        return duplicate

    @staticmethod
    @transaction.atomic
    def duplicate_album(album: Album, *, actor) -> Album:
        """Create a draft metadata copy without duplicating durable tracks."""
        EditorialService._require(actor, "catalog.change_album")
        duplicate = Album.objects.create(
            title_ne=album.title_ne,
            title_en=album.title_en,
            description_ne=album.description_ne,
            description_en=album.description_en,
            cover_image=album.cover_image,
            author=album.author,
            album_type=album.album_type,
            release_date=album.release_date,
            is_featured=False,
            is_published=False,
        )
        duplicate.genres.set(album.genres.all())
        duplicate.moods.set(album.moods.all())
        return duplicate

    @staticmethod
    @transaction.atomic
    def set_published(queryset, *, value: bool, actor) -> EditorialResult:
        permission = (
            "catalog.change_album"
            if queryset.model is Album
            else "playlists.change_playlist"
        )
        EditorialService._require(actor, permission)
        total = queryset.count()
        if queryset.model not in {Album, Playlist}:
            raise TypeError(
                "This publication transition supports albums and playlists."
            )
        now = timezone.now()
        eligible = queryset.exclude(is_published=value)
        updated = eligible.update(is_published=value, updated_at=now)
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def publish_tracks(queryset, *, actor=None) -> EditorialResult:
        EditorialService._require(actor, "catalog.publish_audiotrack")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(
            is_published=False,
            processing_status=TrackProcessingStatus.READY,
            review_status=TrackReviewStatus.APPROVED,
        )
        tracks = list(
            eligible.select_related(
                "work__author",
                "narrator",
                "narrator__user",
            )
        )
        updated = eligible.update(is_published=True, published_at=now, updated_at=now)
        for track in tracks:
            notification_service.track_published(track)
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def submit_tracks_for_review(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.change_audiotrack")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(
            is_published=False,
            processing_status=TrackProcessingStatus.READY,
            review_status__in=(
                TrackReviewStatus.DRAFT,
                TrackReviewStatus.REJECTED,
            ),
        )
        updated = eligible.update(
            review_status=TrackReviewStatus.SUBMITTED,
            submitted_at=now,
            reviewed_at=None,
            reviewed_by=None,
            updated_at=now,
        )
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def approve_tracks(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.approve_audiotrack")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(
            is_published=False,
            processing_status=TrackProcessingStatus.READY,
            review_status=TrackReviewStatus.SUBMITTED,
        )
        tracks = list(
            eligible.select_related("narrator__user").prefetch_related(
                "contributors__creator"
            )
        )
        updated = eligible.update(
            review_status=TrackReviewStatus.APPROVED,
            reviewed_at=now,
            reviewed_by=actor,
            updated_at=now,
        )
        for track in tracks:
            notification_service.creator_submission_approved(track)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def approve_and_publish_tracks(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.publish_audiotrack")
        EditorialService._require(actor, "catalog.approve_audiotrack")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(
            is_published=False,
            processing_status=TrackProcessingStatus.READY,
            review_status=TrackReviewStatus.SUBMITTED,
        )
        tracks = list(
            eligible.select_related(
                "work__author",
                "narrator",
                "narrator__user",
            ).prefetch_related("contributors__creator")
        )
        updated = eligible.update(
            review_status=TrackReviewStatus.APPROVED,
            reviewed_at=now,
            reviewed_by=actor,
            is_published=True,
            published_at=now,
            updated_at=now,
        )
        for track in tracks:
            notification_service.track_published(
                track,
                include_creator_approval=True,
            )
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def reject_tracks(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.approve_audiotrack")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(
            is_published=False,
            review_status=TrackReviewStatus.SUBMITTED,
        )
        tracks = list(
            eligible.select_related("narrator__user").prefetch_related(
                "contributors__creator"
            )
        )
        updated = eligible.update(
            review_status=TrackReviewStatus.REJECTED,
            reviewed_at=now,
            reviewed_by=actor,
            updated_at=now,
        )
        for track in tracks:
            notification_service.creator_submission_rejected(track)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def unpublish_tracks(queryset, *, actor) -> EditorialResult:
        EditorialService._require(actor, "catalog.publish_audiotrack")
        total = queryset.count()
        now = timezone.now()
        eligible = queryset.filter(is_published=True)
        updated = eligible.update(is_published=False, published_at=None, updated_at=now)
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def retry_processing(queryset, *, actor=None) -> EditorialResult:
        EditorialService._require(actor, "catalog.retry_audioprocessingjob")
        total = queryset.count()
        now = timezone.now()
        track_ids = list(queryset.values_list("pk", flat=True))
        jobs = list(
            AudioProcessingJob.objects.select_for_update()
            .filter(
                track_id__in=track_ids,
                track__processing_status=TrackProcessingStatus.FAILED,
                status=AudioProcessingJobStatus.FAILED,
                attempts__lt=F("max_attempts"),
            )
            .order_by("pk")
        )
        job_track_ids = {job.track_id for job in jobs}
        missing_track_ids = list(
            queryset.filter(
                processing_status=TrackProcessingStatus.FAILED,
                processing_job__isnull=True,
            ).values_list("pk", flat=True)
        )
        if missing_track_ids:
            AudioProcessingJob.objects.bulk_create(
                [
                    AudioProcessingJob(
                        track_id=track_id,
                        status=AudioProcessingJobStatus.QUEUED,
                        retry_initiated_by=actor,
                        retry_requested_at=now,
                    )
                    for track_id in missing_track_ids
                ],
                ignore_conflicts=True,
            )
            jobs.extend(
                AudioProcessingJob.objects.filter(
                    track_id__in=missing_track_ids,
                    status=AudioProcessingJobStatus.QUEUED,
                ).exclude(track_id__in=job_track_ids)
            )
        job_ids = [job.pk for job in jobs]
        eligible_ids = [job.track_id for job in jobs]
        updated = AudioProcessingJob.objects.filter(pk__in=job_ids).update(
            status=AudioProcessingJobStatus.QUEUED,
            error_summary="",
            technical_error="",
            retry_initiated_by=actor,
            retry_requested_at=now,
            updated_at=now,
        )
        queryset.filter(pk__in=eligible_ids).update(
            processing_status=TrackProcessingStatus.PENDING, updated_at=now
        )
        # The incoming queryset may itself be constrained by the related job's
        # failed status. Fetch by the materialized eligible IDs after updating
        # jobs so the audit rows cannot disappear through lazy re-evaluation.
        for track in queryset.model._base_manager.filter(pk__in=eligible_ids):
            administrative_audit_service.record(
                actor=actor,
                action=AdministrativeAuditAction.PROCESSING_RETRIED,
                obj=track,
                reason="Manual audio-processing retry requested.",
                before={"processing_status": TrackProcessingStatus.FAILED},
                after={"processing_status": TrackProcessingStatus.PENDING},
            )
        if job_ids:
            from apps.catalog.tasks import process_audio_job

            transaction.on_commit(
                lambda: [process_audio_job.delay(str(job_id)) for job_id in job_ids]
            )
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def set_featured(queryset, *, value: bool, actor) -> EditorialResult:
        EditorialService._require(
            actor,
            f"{queryset.model._meta.app_label}.change_{queryset.model._meta.model_name}",
        )
        total = queryset.count()
        eligible = queryset.exclude(is_featured=value)
        if queryset.model is Playlist and value:
            eligible = eligible.filter(playlist_type=PlaylistType.EDITORIAL)
        now = timezone.now()
        updated = eligible.update(is_featured=value, updated_at=now)
        public_cache_invalidation.for_model(queryset.model)
        return EditorialResult(updated, total - updated)
