import csv
from io import StringIO

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import (
    AudioTrack,
    CopyrightStatus,
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db


def staff_with(*codenames):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=("view_audiotrack", "change_audiotrack", *codenames),
        )
    )
    return user


def test_publish_action_requires_confirmation_and_reports_invalid_item(client):
    actor = staff_with("publish_audiotrack")
    ready = AudioTrackFactory(
        processing_status=TrackProcessingStatus.READY,
        review_status=TrackReviewStatus.APPROVED,
        is_published=False,
        published_at=None,
        work__copyright_status=CopyrightStatus.PUBLIC_DOMAIN,
    )
    invalid = AudioTrackFactory(
        processing_status=TrackProcessingStatus.FAILED,
        review_status=TrackReviewStatus.APPROVED,
        is_published=False,
        published_at=None,
    )
    client.force_login(actor)
    url = reverse("admin:catalog_audiotrack_changelist")
    payload = {
        "action": "publish_selected",
        "_selected_action": [str(ready.pk), str(invalid.pk)],
    }

    confirmation = client.post(url, payload)
    assert confirmation.status_code == 200
    assert b"Publish selected tracks" in confirmation.content
    ready.refresh_from_db()
    assert ready.is_published is False

    response = client.post(url, {**payload, "confirm_bulk_action": "1"}, follow=True)
    ready.refresh_from_db()
    invalid.refresh_from_db()

    assert response.status_code == 200
    assert ready.is_published is True
    assert invalid.is_published is False
    messages = [str(message) for message in response.context["messages"]]
    assert any("Published 1" in message for message in messages)
    assert any("Audio processing must be ready" in message for message in messages)


def test_retry_action_reports_non_failed_tracks(client):
    actor = staff_with("retry_audioprocessingjob")
    track = AudioTrackFactory(processing_status=TrackProcessingStatus.READY)
    client.force_login(actor)
    url = reverse("admin:catalog_audiotrack_changelist")
    payload = {
        "action": "retry_processing",
        "_selected_action": str(track.pk),
        "confirm_bulk_action": "1",
    }

    response = client.post(url, payload, follow=True)

    assert response.status_code == 200
    assert any(
        "not failed" in str(message).lower() for message in response.context["messages"]
    )


def test_metadata_export_contains_no_private_media_or_transcript(client):
    actor = staff_with()
    track = AudioTrackFactory(
        transcript="private transcript",
        audio_master_file="originals/private.mp3",
        stream_file_high="processed/private-high.mp3",
    )
    client.force_login(actor)

    response = client.post(
        reverse("admin:catalog_audiotrack_changelist"),
        {
            "action": "export_selected_metadata",
            "_selected_action": str(track.pk),
        },
    )

    assert response.status_code == 200
    rows = list(csv.reader(StringIO(response.content.decode())))
    assert "transcript" not in rows[0]
    assert "audio_master_file" not in rows[0]
    assert "private transcript" not in response.content.decode()


def test_unfold_actions_expose_icons_and_permissions():
    model_admin = admin.site._registry[AudioTrack]

    assert model_admin.publish_selected.icon == "publish"
    assert model_admin.publish_selected.allowed_permissions == ("publish",)
    assert model_admin.retry_processing.icon == "restart_alt"
