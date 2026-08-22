from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.urls import reverse
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    MultipleChoicesDropdownFilter,
    RangeDateTimeFilter,
    RangeNumericFilter,
)

from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import (
    AlbumAdmin,
    AlbumTrackInline,
    AudioTrackAdmin,
    TrackProcessingStateFilter,
)
from apps.catalog.models import (
    Album,
    AudioTrack,
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db


def test_track_duration_formatting():
    model_admin = AudioTrackAdmin(AudioTrack, AdminSite())
    assert model_admin.format_duration(65) == "1:05"
    assert model_admin.format_duration(3661) == "1:01:01"


def test_processing_indicator_uses_status_label():
    track = AudioTrackFactory(
        processing_status=TrackProcessingStatus.FAILED,
        is_published=False,
        published_at=None,
    )
    model_admin = AudioTrackAdmin(AudioTrack, AdminSite())
    assert "Failed" in str(model_admin.processing_indicator(track))
    assert "error" in str(model_admin.processing_indicator(track))
    assert "worker logs" in model_admin.processing_guidance(track)


def test_track_admin_has_requested_columns_filters_search_and_sections():
    model_admin = admin.site._registry[AudioTrack]

    assert model_admin.list_display == (
        "cover_thumbnail",
        "title_ne",
        "work",
        "narrator",
        "album",
        "track_number",
        "formatted_duration",
        "processing_indicator",
        "review_status",
        "publication_indicator",
        "premium_indicator",
        "play_count_cache",
        "published_at",
    )
    assert model_admin.list_filter == (
        TrackProcessingStateFilter,
        ("review_status", MultipleChoicesDropdownFilter),
        ("is_published", BooleanRadioFilter),
        ("is_premium", BooleanRadioFilter),
        ("narrator", AutocompleteSelectFilter),
        ("work__author", AutocompleteSelectFilter),
        ("work__category", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
        ("published_at", RangeDateTimeFilter),
        ("duration_seconds", RangeNumericFilter),
    )
    assert [fieldset[0] for fieldset in model_admin.fieldsets] == [
        "Basic Metadata",
        "Literary Relationships",
        "Narration",
        "Audio Files",
        "Spoken Introduction",
        "Transcript",
        "Processing",
        "Access and Monetization",
        "Publication",
        "Analytics",
        "System Metadata",
    ]
    assert "waveform_data" not in {
        field for _, options in model_admin.fieldsets for field in options["fields"]
    }
    assert {"submit_for_review", "approve_selected", "publish_selected"} <= set(
        model_admin.actions
    )


def test_review_actions_are_hidden_without_explicit_role_permissions(rf):
    model_admin = admin.site._registry[AudioTrack]
    ordinary_staff = UserFactory(is_staff=True)
    request = rf.get("/admin/catalog/audiotrack/")
    request.user = ordinary_staff

    actions = model_admin.get_actions(request)

    assert "submit_for_review" not in actions
    assert "approve_selected" not in actions
    assert "request_changes_selected" not in actions
    assert "reject_selected" not in actions
    assert "schedule_selected" not in actions
    assert "publish_selected" not in actions
    assert "archive_selected" not in actions


def test_submit_for_review_admin_action_confirms_and_transitions(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.READY,
        review_status=TrackReviewStatus.DRAFT,
    )
    client.force_login(user)
    url = reverse("admin:catalog_audiotrack_changelist")
    selection = {
        "action": "submit_for_review",
        helpers.ACTION_CHECKBOX_NAME: str(track.pk),
    }

    confirmation = client.post(url, selection)
    response = client.post(url, {**selection, "confirm_bulk_action": "1"})

    track.refresh_from_db()
    assert confirmation.status_code == 200
    assert response.status_code == 302
    assert track.review_status == TrackReviewStatus.SUBMITTED


def test_track_admin_searches_all_requested_relationships():
    model_admin = admin.site._registry[AudioTrack]

    assert model_admin.search_fields == (
        "=id",
        "slug",
        "title_ne",
        "title_en",
        "work__title_ne",
        "work__title_en",
        "work__author__name_ne",
        "work__author__name_en",
        "narrator__name_ne",
        "narrator__name_en",
        "album__title_ne",
        "album__title_en",
    )


def test_track_audio_availability_quality_and_waveform_summary():
    track = AudioTrackFactory(
        stream_file_high="processed/audio/test/high.mp3",
        stream_file_low="",
        waveform_data=[0.1, 0.2, 0.3],
    )
    model_admin = admin.site._registry[AudioTrack]

    assert "High: available" in str(model_admin.audio_file_availability(track))
    assert "Low: missing" in str(model_admin.audio_file_availability(track))
    assert model_admin.audio_quality_summary(track) == "High"
    assert "3 waveform samples" in model_admin.waveform_summary(track)
    assert "waveform_data" not in model_admin.readonly_fields


def test_non_ready_track_has_clear_publication_block():
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
        review_status=TrackReviewStatus.APPROVED,
    )
    model_admin = admin.site._registry[AudioTrack]

    assert "in progress" in model_admin.processing_guidance(track)
    assert model_admin.publication_indicator(track) == ("draft", "Draft")
    assert model_admin.publication_readiness(track) == (
        "blocked",
        "Blocked: audio processing is not ready",
    )


def test_cloudfront_preview_uses_permission_checked_lazy_delivery(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        stream_file_high="processed/audio/test/high.mp3",
    )
    deliver = Mock(
        return_value={
            "quality": "high",
            "url": "https://audio.example.com/signed",
            "expiresAt": None,
        }
    )
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)
    url = reverse(
        "admin:catalog_audiotrack_audio_delivery",
        kwargs={"object_id": track.pk, "quality": "high"},
    )

    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "quality": "high",
        "url": "https://audio.example.com/signed",
        "expiresAt": None,
    }
    assert "private" in response.headers["Cache-Control"]
    assert "no-store" in response.headers["Cache-Control"]
    deliver.assert_called_once()


def test_audio_preview_widget_does_not_sign_on_change_or_list_pages(
    client, monkeypatch
):
    user = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        stream_file_high="processed/audio/test/high.mp3",
        stream_file_low="processed/audio/test/low.mp3",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    change = client.get(reverse("admin:catalog_audiotrack_change", args=(track.pk,)))
    listing = client.get(reverse("admin:catalog_audiotrack_changelist"))

    assert change.status_code == 200
    assert b"data-secure-audio-preview" in change.content
    assert b"data-play" in change.content
    assert b"data-seek" in change.content
    assert b"data-volume" in change.content
    assert b"data-speed" in change.content
    assert b"autoplay" not in change.content
    assert listing.status_code == 200
    assert b"data-secure-audio-preview" not in listing.content
    deliver.assert_not_called()


def test_processing_review_change_page_uses_secure_widget(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
        stream_file_low="processed/audio/test/low.mp3",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    response = client.get(reverse("admin:catalog_audiotrack_change", args=(track.pk,)))

    assert response.status_code == 200
    assert b"data-secure-audio-preview" in response.content
    assert b"Audio processing is currently in progress" in response.content
    deliver.assert_not_called()


def test_audio_delivery_rejects_staff_without_track_permission(client, monkeypatch):
    user = UserFactory(is_staff=True)
    track = AudioTrackFactory(stream_file_low="processed/audio/test/low.mp3")
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)
    url = reverse(
        "admin:catalog_audiotrack_audio_delivery",
        kwargs={"object_id": track.pk, "quality": "low"},
    )

    response = client.get(url)

    assert response.status_code == 403
    deliver.assert_not_called()


def test_audio_delivery_redirects_anonymous_users_without_signing(client, monkeypatch):
    track = AudioTrackFactory(stream_file_low="processed/audio/test/low.mp3")
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    url = reverse(
        "admin:catalog_audiotrack_audio_delivery",
        kwargs={"object_id": track.pk, "quality": "low"},
    )

    response = client.get(url)

    assert response.status_code == 302
    assert reverse("admin:login") in response.url
    deliver.assert_not_called()


def test_audio_delivery_allows_staff_with_view_permission(client, monkeypatch):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="catalog",
            codename="view_audiotrack",
        )
    )
    track = AudioTrackFactory(stream_file_low="processed/audio/test/low.mp3")
    deliver = Mock(
        return_value={
            "quality": "low",
            "url": "https://audio.example.com/signed",
            "expiresAt": None,
        }
    )
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)
    url = reverse(
        "admin:catalog_audiotrack_audio_delivery",
        kwargs={"object_id": track.pk, "quality": "low"},
    )

    response = client.get(url)

    assert response.status_code == 200
    deliver.assert_called_once()


def test_audio_delivery_rejects_unavailable_quality_without_signing(
    client, monkeypatch
):
    user = UserFactory(is_staff=True, is_superuser=True)
    track = AudioTrackFactory(
        stream_file_low="",
        stream_file_high="processed/audio/test/high.mp3",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)
    url = reverse(
        "admin:catalog_audiotrack_audio_delivery",
        kwargs={"object_id": track.pk, "quality": "low"},
    )

    response = client.get(url)

    assert response.status_code == 404
    assert response.json()["code"] == "audio_unavailable"
    deliver.assert_not_called()


def test_album_tracks_are_a_read_only_linked_inline():
    inline = AlbumTrackInline(Album, AdminSite())
    request = RequestFactory().get("/admin/")
    request.user = UserFactory(is_staff=True)
    assert inline.show_change_link
    assert not inline.has_add_permission(request)
    assert not inline.has_delete_permission(request)
    assert AlbumTrackInline in AlbumAdmin.inlines


def test_only_superusers_can_delete_tracks_in_admin():
    request = RequestFactory().get("/admin/")
    request.user = UserFactory(is_superuser=True, is_staff=True)
    model_admin = AudioTrackAdmin(AudioTrack, AdminSite())
    assert model_admin.has_delete_permission(request)

    request.user = UserFactory(is_superuser=False, is_staff=True)
    assert not model_admin.has_delete_permission(request)
