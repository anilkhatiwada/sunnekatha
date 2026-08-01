import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import PendingReviewTrackAdmin
from apps.catalog.models import (
    CopyrightStatus,
    PendingReviewTrack,
    TrackProcessingStatus,
    TrackReviewEvent,
    TrackReviewStatus,
)
from apps.catalog.review_workflow import (
    pending_review_service,
    review_attention_issues,
    review_readiness_issues,
)
from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db


def editor():
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="catalog",
            codename="approve_audiotrack",
        )
    )
    return user.__class__.objects.get(pk=user.pk)


def pending_track(**kwargs):
    return AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.SUBMITTED,
        **kwargs,
    )


def test_pending_review_proxy_is_registered_with_safe_actions_only():
    model_admin = admin.site._registry[PendingReviewTrack]

    assert isinstance(model_admin, PendingReviewTrackAdmin)
    assert set(model_admin.actions) == {
        "assign_reviewer",
        "approve_safe_selected",
        "request_changes_selected",
    }
    assert "publish_selected" not in model_admin.actions


def test_pending_review_page_requires_editor_permission(client):
    ordinary_staff = UserFactory(is_staff=True)
    authorized_editor = editor()
    url = reverse("admin:catalog_pendingreviewtrack_changelist")

    client.force_login(ordinary_staff)
    denied = client.get(url)
    client.force_login(authorized_editor)
    allowed = client.get(url)

    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_pending_page_only_lists_submitted_tracks_and_supports_filters(client):
    reviewer = editor()
    matching = pending_track(
        content_type="story",
        processing_status=TrackProcessingStatus.FAILED,
        reviewed_by=reviewer,
    )
    matching.work.copyright_status = CopyrightStatus.UNKNOWN
    matching.work.save(update_fields=("copyright_status", "updated_at"))
    other_type = pending_track()
    other_type.work.content_type = "poem"
    other_type.work.save(update_fields=("content_type", "updated_at"))
    other_type.save(update_fields=("content_type", "updated_at"))
    AudioTrackFactory(review_status=TrackReviewStatus.DRAFT)
    client.force_login(reviewer)

    response = client.get(
        reverse("admin:catalog_pendingreviewtrack_changelist"),
        {
            "content_type": "story",
            "processing_status": TrackProcessingStatus.FAILED,
            "work__copyright_status": CopyrightStatus.UNKNOWN,
            "reviewed_by": reviewer.pk,
            "q": matching.title_ne,
        },
    )

    assert response.status_code == 200
    assert list(response.context["cl"].queryset) == [matching]


def test_pending_page_filters_by_creator_or_uploader(client):
    reviewer = editor()
    creator = UserFactory(is_creator=True)
    matching = pending_track()
    matching.narrator.user = creator
    matching.narrator.save(update_fields=("user", "updated_at"))
    pending_track()
    client.force_login(reviewer)

    response = client.get(
        reverse("admin:catalog_pendingreviewtrack_changelist"),
        {"creator": creator.pk},
    )

    assert response.status_code == 200
    assert list(response.context["cl"].queryset) == [matching]


def test_attention_flags_show_non_blocking_editorial_warnings():
    track = pending_track(processing_status=TrackProcessingStatus.FAILED)
    track.work.copyright_status = CopyrightStatus.UNKNOWN
    track.work.cover_image = ""
    track.work.save(update_fields=("copyright_status", "cover_image", "updated_at"))

    issues = review_attention_issues(track)

    assert "Audio processing is not ready" in issues
    assert "Copyright status is unknown" in issues
    assert "Cover image is missing" in issues
    assert review_readiness_issues(track) == ("Audio processing is not ready",)


def test_assign_reviewer_records_assignment_and_audit_event():
    actor = editor()
    reviewer = editor()
    track = pending_track()

    result = pending_review_service.assign_reviewer(
        queryset=PendingReviewTrack.objects.filter(pk=track.pk),
        reviewer=reviewer,
        actor=actor,
    )

    track.refresh_from_db()
    assert result.updated == 1
    assert track.reviewed_by == reviewer
    event = TrackReviewEvent.objects.get(track=track)
    assert event.actor == actor
    assert event.from_status == event.to_status == TrackReviewStatus.SUBMITTED
    assert "Reviewer assigned" in event.comment


def test_safe_approval_blocks_only_unready_audio_and_never_publishes():
    actor = editor()
    ready = pending_track()
    blocked = pending_track(processing_status=TrackProcessingStatus.FAILED)
    ready.work.copyright_status = CopyrightStatus.UNKNOWN
    ready.work.cover_image = ""
    ready.work.save(update_fields=("copyright_status", "cover_image", "updated_at"))

    result = pending_review_service.approve_safe(
        queryset=PendingReviewTrack.objects.filter(
            pk__in=(ready.pk, blocked.pk)
        ).prefetch_related("contributors"),
        actor=actor,
    )

    ready.refresh_from_db()
    blocked.refresh_from_db()
    assert result.updated == 1
    assert result.skipped == 1
    assert ready.review_status == TrackReviewStatus.APPROVED
    assert ready.is_published is False
    assert blocked.review_status == TrackReviewStatus.SUBMITTED
    assert blocked.is_published is False


def test_open_review_link_uses_full_audio_track_admin():
    model_admin = admin.site._registry[PendingReviewTrack]
    track = pending_track()

    link = str(model_admin.open_review_page(track))

    assert reverse("admin:catalog_audiotrack_change", args=(track.pk,)) in link
