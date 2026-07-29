import pytest
from django.core.exceptions import PermissionDenied

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import TrackProcessingStatus, TrackReviewStatus
from apps.catalog.services import EditorialResult, EditorialService
from apps.catalog.tests.factories import (
    AlbumFactory,
    AudioProcessingJobFactory,
    AudioTrackFactory,
    LiteraryWorkFactory,
)
from apps.creators.models import ContentContributor, CreatorProfile, CreatorRole
from apps.notifications.models import Notification, NotificationType
from apps.taxonomy.tests.factories import GenreFactory, MoodFactory

pytestmark = pytest.mark.django_db


def test_editorial_service_rejects_unauthorized_staff():
    work = LiteraryWorkFactory(is_published=False, published_at=None)

    with pytest.raises(PermissionDenied):
        EditorialService.publish_works(
            work.__class__.objects.filter(pk=work.pk),
            actor=UserFactory(is_staff=True),
        )


def test_work_publication_transitions_set_and_clear_timestamp():
    actor = UserFactory(is_staff=True, is_superuser=True)
    work = LiteraryWorkFactory(is_published=False, published_at=None)

    result = EditorialService.publish_works(
        LiteraryWorkFactory._meta.model.objects.filter(pk=work.pk),
        actor=actor,
    )
    work.refresh_from_db()

    assert result.updated == 1
    assert work.is_published
    assert work.published_at is not None

    EditorialService.unpublish_works(
        LiteraryWorkFactory._meta.model.objects.filter(pk=work.pk),
        actor=actor,
    )
    work.refresh_from_db()
    assert not work.is_published
    assert work.published_at is None


def test_duplicate_work_copies_editorial_metadata_as_an_unpublished_draft():
    actor = UserFactory(is_staff=True, is_superuser=True)
    source = LiteraryWorkFactory(
        title_ne="मूल कृति",
        is_published=True,
        is_featured=True,
    )
    source.genres.add(GenreFactory())
    source.moods.add(MoodFactory())

    duplicate = EditorialService.duplicate_work(source, actor=actor)

    assert duplicate.pk != source.pk
    assert duplicate.title_ne == source.title_ne
    assert duplicate.slug != source.slug
    assert duplicate.author == source.author
    assert duplicate.language == source.language
    assert set(duplicate.genres.all()) == set(source.genres.all())
    assert set(duplicate.moods.all()) == set(source.moods.all())
    assert duplicate.is_published is False
    assert duplicate.is_featured is False
    assert duplicate.published_at is None
    assert duplicate.audio_tracks.count() == 0


def test_track_publish_skips_tracks_that_are_not_approved_and_ready():
    actor = UserFactory(is_staff=True, is_superuser=True)
    approved = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.APPROVED,
        processing_status=TrackProcessingStatus.READY,
    )
    failed = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.APPROVED,
        processing_status=TrackProcessingStatus.FAILED,
    )

    result = EditorialService.publish_tracks(
        approved.__class__.objects.filter(pk__in=(approved.pk, failed.pk)),
        actor=actor,
    )

    approved.refresh_from_db()
    failed.refresh_from_db()
    assert result.updated == 1
    assert result.skipped == 1
    assert approved.is_published
    assert not failed.is_published


def test_submit_for_review_only_accepts_ready_drafts():
    actor = UserFactory(is_staff=True, is_superuser=True)
    ready = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
        processing_status=TrackProcessingStatus.READY,
    )
    processing = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
        processing_status=TrackProcessingStatus.PROCESSING,
    )

    result = EditorialService.submit_tracks_for_review(
        ready.__class__.objects.filter(pk__in=(ready.pk, processing.pk)),
        actor=actor,
    )
    ready.refresh_from_db()
    processing.refresh_from_db()

    assert result == EditorialResult(updated=1, skipped=1)
    assert ready.review_status == TrackReviewStatus.SUBMITTED
    assert ready.submitted_at is not None
    assert processing.review_status == TrackReviewStatus.DRAFT


def test_approve_tracks_records_reviewer_without_publishing():
    reviewer = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.SUBMITTED,
        processing_status=TrackProcessingStatus.READY,
    )

    result = EditorialService.approve_tracks(
        track.__class__.objects.filter(pk=track.pk),
        actor=reviewer,
    )
    track.refresh_from_db()

    assert result == EditorialResult(updated=1, skipped=0)
    assert track.review_status == TrackReviewStatus.APPROVED
    assert track.reviewed_by == reviewer
    assert track.reviewed_at is not None
    assert track.is_published is False


def test_approve_and_publish_records_reviewer():
    reviewer = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.SUBMITTED,
        processing_status=TrackProcessingStatus.READY,
    )

    result = EditorialService.approve_and_publish_tracks(
        track.__class__.objects.filter(pk=track.pk),
        actor=reviewer,
    )
    track.refresh_from_db()

    assert result.updated == 1
    assert track.review_status == TrackReviewStatus.APPROVED
    assert track.reviewed_by == reviewer
    assert track.reviewed_at is not None
    assert track.is_published


def test_retry_processing_only_resets_failed_tracks():
    actor = UserFactory(is_staff=True, is_superuser=True)
    failed = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.FAILED,
    )
    ready = AudioTrackFactory(processing_status=TrackProcessingStatus.READY)

    result = EditorialService.retry_processing(
        failed.__class__.objects.filter(pk__in=(failed.pk, ready.pk)),
        actor=actor,
    )

    failed.refresh_from_db()
    ready.refresh_from_db()
    assert result == EditorialResult(updated=1, skipped=1)
    assert failed.processing_status == TrackProcessingStatus.PENDING
    assert ready.processing_status == TrackProcessingStatus.READY


def test_retry_processing_requeues_eligible_job_and_skips_exhausted_job():
    actor = UserFactory(is_staff=True, is_superuser=True)
    eligible_job = AudioProcessingJobFactory(
        status="failed",
        attempts=1,
        max_attempts=3,
        track__processing_status=TrackProcessingStatus.FAILED,
    )
    exhausted_job = AudioProcessingJobFactory(
        status="failed",
        attempts=3,
        max_attempts=3,
        track__processing_status=TrackProcessingStatus.FAILED,
    )

    result = EditorialService.retry_processing(
        eligible_job.track.__class__.objects.filter(
            pk__in=(eligible_job.track_id, exhausted_job.track_id)
        ),
        actor=actor,
    )
    eligible_job.refresh_from_db()
    eligible_job.track.refresh_from_db()
    exhausted_job.refresh_from_db()
    exhausted_job.track.refresh_from_db()

    assert result == EditorialResult(updated=1, skipped=1)
    assert eligible_job.status == "queued"
    assert eligible_job.track.processing_status == TrackProcessingStatus.PENDING
    assert exhausted_job.status == "failed"
    assert exhausted_job.track.processing_status == TrackProcessingStatus.FAILED


def test_album_publication_uses_generic_transition():
    actor = UserFactory(is_staff=True, is_superuser=True)
    album = AlbumFactory(is_published=False)
    result = EditorialService.set_published(
        album.__class__.objects.filter(pk=album.pk),
        value=True,
        actor=actor,
    )
    album.refresh_from_db()
    assert result.updated == 1
    assert album.is_published


def test_reject_submission_records_staff_reviewer_and_notifies_creator():
    reviewer = UserFactory(is_staff=True, is_superuser=True)
    creator_user = UserFactory(is_creator=True)
    creator = CreatorProfile.objects.create(
        user=creator_user,
        display_name="Creator",
        roles=[CreatorRole.CONTENT_UPLOADER],
        is_approved=True,
    )
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.SUBMITTED,
    )
    ContentContributor.objects.create(
        track=track,
        creator=creator,
        role=CreatorRole.CONTENT_UPLOADER,
    )

    result = EditorialService.reject_tracks(
        track.__class__.objects.filter(pk=track.pk),
        actor=reviewer,
    )
    track.refresh_from_db()

    assert result == EditorialResult(updated=1, skipped=0)
    assert track.review_status == TrackReviewStatus.REJECTED
    assert track.reviewed_by == reviewer
    assert track.reviewed_at is not None
    assert not track.is_published
    assert Notification.objects.filter(
        recipient=creator_user,
        notification_type=NotificationType.CREATOR_SUBMISSION_REJECTED,
    ).exists()
