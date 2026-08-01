from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import (
    CopyrightStatus,
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.catalog.review_workflow import track_review_workflow
from apps.catalog.scheduled_publications import scheduled_publication_admin_service
from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db


def track_staff(*codenames):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=codenames,
        )
    )
    return user


def scheduled_track(*, scheduled_for=None, **kwargs):
    return AudioTrackFactory(
        review_status=TrackReviewStatus.SCHEDULED,
        is_published=True,
        published_at=scheduled_for or timezone.now() + timedelta(days=1),
        **kwargs,
    )


def test_page_is_staff_permission_aware_and_displays_required_columns(client):
    track = scheduled_track()
    viewer = track_staff("view_audiotrack")
    client.force_login(viewer)

    response = client.get(reverse("admin:catalog_scheduled_publications"))

    assert response.status_code == 200
    content = response.content.decode()
    assert track.title_ne in content
    for heading in (
        "Content title",
        "Content type",
        "Author",
        "Narrator",
        "Scheduled time",
        "Processing readiness",
        "Copyright readiness",
        "Publication status",
        "Assigned editor",
    ):
        assert heading in content
    for group_title in ("Today", "Tomorrow", "This week", "Later"):
        assert group_title in content
    assert "Open content" in content
    assert "Publish now" not in content


def test_viewer_cannot_invoke_publication_actions(client):
    track = scheduled_track()
    client.force_login(track_staff("view_audiotrack"))

    response = client.post(
        reverse("admin:catalog_scheduled_publications"),
        {"track_id": str(track.pk), "publication_action": "publish"},
    )

    assert response.status_code == 403
    track.refresh_from_db()
    assert track.review_status == TrackReviewStatus.SCHEDULED


def test_groups_use_configured_timezone():
    with timezone.override("Asia/Kathmandu"):
        local_today = timezone.localdate()
        midnight_tomorrow = timezone.make_aware(
            datetime.combine(local_today + timedelta(days=1), time(hour=0, minute=15))
        )
        track = scheduled_track(scheduled_for=midnight_tomorrow)

        groups = scheduled_publication_admin_service.get_groups(
            now=timezone.make_aware(
                datetime.combine(local_today, time(hour=23)),
            )
        )

    tomorrow = next(group for group in groups if group.identifier == "tomorrow")
    assert [item["id"] for item in tomorrow.items] == [track.pk]
    assert timezone.is_aware(tomorrow.items[0]["scheduled_time"])


def test_reschedule_converts_local_form_time_to_aware_database_value(client):
    track = scheduled_track()
    publisher = track_staff("view_audiotrack", "publish_audiotrack")
    client.force_login(publisher)

    with timezone.override("Asia/Kathmandu"):
        local_target = timezone.localtime(timezone.now() + timedelta(days=3)).replace(
            second=0,
            microsecond=0,
        )
        response = client.post(
            reverse("admin:catalog_scheduled_publications"),
            {
                "track_id": str(track.pk),
                "publication_action": "reschedule",
                "scheduled_for": local_target.strftime("%Y-%m-%dT%H:%M"),
            },
        )

    track.refresh_from_db()
    assert response.status_code == 302
    assert timezone.is_aware(track.published_at)
    assert track.published_at == local_target
    event = track.review_events.latest("created_at")
    assert event.scheduled_for == local_target
    assert event.actor == publisher


def test_cancel_and_publish_now_use_review_workflow(client):
    canceled = scheduled_track()
    published = scheduled_track()
    publisher = track_staff("view_audiotrack", "publish_audiotrack")
    client.force_login(publisher)
    url = reverse("admin:catalog_scheduled_publications")

    cancel_response = client.post(
        url,
        {
            "track_id": str(canceled.pk),
            "publication_action": "cancel",
        },
    )
    canceled.refresh_from_db()
    assert cancel_response.status_code == 200
    assert b"Cancel the scheduled publication" in cancel_response.content
    assert canceled.review_status == TrackReviewStatus.SCHEDULED

    cancel_response = client.post(
        url,
        {
            "track_id": str(canceled.pk),
            "publication_action": "cancel",
            "confirmed": "yes",
        },
    )
    publish_response = client.post(
        url,
        {
            "track_id": str(published.pk),
            "publication_action": "publish",
        },
    )
    published.refresh_from_db()
    assert publish_response.status_code == 200
    assert b"Publish" in publish_response.content
    assert published.review_status == TrackReviewStatus.SCHEDULED

    publish_response = client.post(
        url,
        {
            "track_id": str(published.pk),
            "publication_action": "publish",
            "confirmed": "yes",
        },
    )

    canceled.refresh_from_db()
    published.refresh_from_db()
    assert cancel_response.status_code == 302
    assert canceled.review_status == TrackReviewStatus.APPROVED
    assert not canceled.is_published
    assert canceled.published_at is None
    assert publish_response.status_code == 302
    assert published.review_status == TrackReviewStatus.PUBLISHED
    assert published.published_at <= timezone.now()


@override_settings(ENFORCE_EDITORIAL_RIGHTS_READINESS=True)
def test_scheduling_rejects_processing_and_unresolved_rights():
    publisher = track_staff("publish_audiotrack")
    future = timezone.now() + timedelta(days=2)
    processing = AudioTrackFactory(
        review_status=TrackReviewStatus.APPROVED,
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
    )
    unresolved = AudioTrackFactory(
        review_status=TrackReviewStatus.APPROVED,
        is_published=False,
        published_at=None,
    )
    unresolved.work.copyright_status = CopyrightStatus.PERMISSION_PENDING
    unresolved.work.save(update_fields=("copyright_status", "updated_at"))

    with pytest.raises(ValidationError, match="processing"):
        track_review_workflow.transition(
            track_id=processing.pk,
            target=TrackReviewStatus.SCHEDULED,
            actor=publisher,
            scheduled_for=future,
        )
    with pytest.raises(ValidationError, match="Copyright"):
        track_review_workflow.transition(
            track_id=unresolved.pk,
            target=TrackReviewStatus.SCHEDULED,
            actor=publisher,
            scheduled_for=future,
        )


@override_settings(ENFORCE_EDITORIAL_RIGHTS_READINESS=True)
def test_protected_work_requires_verified_effective_audio_permission():
    publisher = track_staff("publish_audiotrack")
    track = AudioTrackFactory(
        review_status=TrackReviewStatus.APPROVED,
        is_published=False,
        published_at=None,
    )
    track.work.copyright_status = CopyrightStatus.PERMISSION_GRANTED
    track.work.copyright_owner = "Rights holder"
    track.work.save(update_fields=("copyright_status", "copyright_owner", "updated_at"))

    with pytest.raises(ValidationError, match="verified, effective audio permission"):
        track_review_workflow.transition(
            track_id=track.pk,
            target=TrackReviewStatus.SCHEDULED,
            actor=publisher,
            scheduled_for=timezone.now() + timedelta(days=1),
        )


def test_rights_warnings_do_not_block_scheduling_by_default():
    publisher = track_staff("publish_audiotrack")
    track = AudioTrackFactory(
        review_status=TrackReviewStatus.APPROVED,
        is_published=False,
        published_at=None,
    )
    track.work.copyright_status = CopyrightStatus.PERMISSION_PENDING
    track.work.save(update_fields=("copyright_status", "updated_at"))

    scheduled = track_review_workflow.transition(
        track_id=track.pk,
        target=TrackReviewStatus.SCHEDULED,
        actor=publisher,
        scheduled_for=timezone.now() + timedelta(days=1),
    )

    assert scheduled.review_status == TrackReviewStatus.SCHEDULED


def test_schedule_page_service_has_fixed_prefetch_query_count():
    for offset in range(1, 5):
        scheduled_track(scheduled_for=timezone.now() + timedelta(days=offset))

    with CaptureQueriesContext(connection) as queries:
        groups = scheduled_publication_admin_service.get_groups()
        items = [item for group in groups for item in group.items]

    assert len(items) == 4
    assert len(queries) <= 3
