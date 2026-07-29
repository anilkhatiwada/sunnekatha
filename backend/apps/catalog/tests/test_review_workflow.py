from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import (
    TrackReviewEvent,
    TrackReviewStatus,
)
from apps.catalog.review_workflow import track_review_workflow
from apps.catalog.tests.factories import AudioTrackFactory
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


def grant(user, *codenames):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=codenames,
        )
    )
    return user.__class__.objects.get(pk=user.pk)


def transition(track, target, actor, **kwargs):
    return track_review_workflow.transition(
        track_id=track.pk,
        target=target,
        actor=actor,
        **kwargs,
    )


def submitted_track():
    return AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.SUBMITTED,
    )


def test_creator_can_submit_owned_draft_but_not_another_creators_track():
    creator = UserFactory(is_creator=True)
    owned = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
    )
    owned.narrator.user = creator
    owned.narrator.save(update_fields=("user", "updated_at"))
    other = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
    )

    result = transition(owned, TrackReviewStatus.SUBMITTED, creator)

    assert result.review_status == TrackReviewStatus.SUBMITTED
    with pytest.raises(PermissionDenied):
        transition(other, TrackReviewStatus.SUBMITTED, creator)


def test_only_editor_permission_can_approve():
    track = submitted_track()
    ordinary_staff = UserFactory(is_staff=True)
    editor = grant(
        UserFactory(is_staff=True),
        "approve_audiotrack",
    )

    with pytest.raises(PermissionDenied):
        transition(track, TrackReviewStatus.APPROVED, ordinary_staff)

    approved = transition(track, TrackReviewStatus.APPROVED, editor)

    assert approved.reviewed_by == editor
    assert approved.reviewed_at is not None
    assert AdministrativeAudit.objects.filter(
        action=AdministrativeAuditAction.APPROVED,
        object_id=str(track.pk),
        staff_user=editor,
    ).exists()


def test_staff_submission_and_rejection_create_semantic_audit_events():
    submitter = grant(UserFactory(is_staff=True), "change_audiotrack")
    reviewer = grant(UserFactory(is_staff=True), "approve_audiotrack")
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
    )

    transition(track, TrackReviewStatus.SUBMITTED, submitter)
    transition(
        track,
        TrackReviewStatus.REJECTED,
        reviewer,
        comment="Rights information is incomplete.",
    )

    assert set(
        AdministrativeAudit.objects.filter(object_id=str(track.pk)).values_list(
            "action",
            flat=True,
        )
    ) == {
        AdministrativeAuditAction.REVIEW_SUBMITTED,
        AdministrativeAuditAction.REJECTED,
    }


def test_creator_cannot_self_approve_without_explicit_permission():
    creator = grant(
        UserFactory(is_staff=True, is_creator=True),
        "approve_audiotrack",
    )
    track = submitted_track()
    track.narrator.user = creator
    track.narrator.save(update_fields=("user", "updated_at"))

    with pytest.raises(PermissionDenied, match="own submissions"):
        transition(track, TrackReviewStatus.APPROVED, creator)

    creator = grant(creator, "approve_own_audiotrack")
    approved = transition(track, TrackReviewStatus.APPROVED, creator)
    assert approved.review_status == TrackReviewStatus.APPROVED


@pytest.mark.parametrize(
    ("target", "expected_notification"),
    [
        (TrackReviewStatus.CHANGES_REQUESTED, "creator_changes_requested"),
        (TrackReviewStatus.REJECTED, "creator_submission_rejected"),
    ],
)
def test_editorial_negative_decisions_require_reason_and_notify_creator(
    target,
    expected_notification,
):
    creator = UserFactory(is_creator=True)
    editor = grant(UserFactory(is_staff=True), "approve_audiotrack")
    track = submitted_track()
    track.narrator.user = creator
    track.narrator.save(update_fields=("user", "updated_at"))

    with pytest.raises(ValidationError, match="reason"):
        transition(track, target, editor)

    reviewed = transition(
        track,
        target,
        editor,
        comment="Please correct the rights documentation.",
    )

    assert reviewed.review_comments == "Please correct the rights documentation."
    event = TrackReviewEvent.objects.get(track=track)
    assert event.actor == editor
    assert event.comment == reviewed.review_comments
    assert Notification.objects.filter(
        recipient=creator,
        notification_type=expected_notification,
    ).exists()


def test_only_publisher_can_schedule_and_schedule_must_be_future():
    approved = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.APPROVED,
    )
    editor = grant(UserFactory(is_staff=True), "approve_audiotrack")
    publisher = grant(UserFactory(is_staff=True), "publish_audiotrack")
    future = timezone.now() + timedelta(days=2)

    with pytest.raises(PermissionDenied):
        transition(
            approved,
            TrackReviewStatus.SCHEDULED,
            editor,
            scheduled_for=future,
        )
    with pytest.raises(ValidationError, match="future"):
        transition(
            approved,
            TrackReviewStatus.SCHEDULED,
            publisher,
            scheduled_for=timezone.now() - timedelta(minutes=1),
        )

    scheduled = transition(
        approved,
        TrackReviewStatus.SCHEDULED,
        publisher,
        scheduled_for=future,
    )
    assert scheduled.review_status == TrackReviewStatus.SCHEDULED
    assert scheduled.is_published is True
    assert scheduled.published_at == future

    published = transition(scheduled, TrackReviewStatus.PUBLISHED, publisher)
    assert published.review_status == TrackReviewStatus.PUBLISHED
    assert published.published_at < future
    assert published.published_at <= timezone.now()


def test_only_publisher_can_publish_and_archive():
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.APPROVED,
    )
    editor = grant(UserFactory(is_staff=True), "approve_audiotrack")
    publisher = grant(UserFactory(is_staff=True), "publish_audiotrack")

    with pytest.raises(PermissionDenied):
        transition(track, TrackReviewStatus.PUBLISHED, editor)

    published = transition(track, TrackReviewStatus.PUBLISHED, publisher)
    assert published.review_status == TrackReviewStatus.PUBLISHED
    assert published.is_published is True

    with pytest.raises(PermissionDenied):
        transition(track, TrackReviewStatus.ARCHIVED, editor)

    archived = transition(track, TrackReviewStatus.ARCHIVED, publisher)
    assert archived.review_status == TrackReviewStatus.ARCHIVED
    assert archived.is_published is False
    assert archived.published_at is None
    assert list(
        TrackReviewEvent.objects.filter(track=track).values_list(
            "to_status",
            flat=True,
        )
    ) == [TrackReviewStatus.ARCHIVED, TrackReviewStatus.PUBLISHED]
    assert set(
        AdministrativeAudit.objects.filter(object_id=str(track.pk)).values_list(
            "action",
            flat=True,
        )
    ) == {
        AdministrativeAuditAction.PUBLISHED,
        AdministrativeAuditAction.UNPUBLISHED,
    }


def test_invalid_state_transition_is_rejected_and_not_audited():
    editor = grant(UserFactory(is_staff=True), "approve_audiotrack")
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
    )

    with pytest.raises(ValidationError, match="Cannot move"):
        transition(track, TrackReviewStatus.APPROVED, editor)

    assert not TrackReviewEvent.objects.filter(track=track).exists()
