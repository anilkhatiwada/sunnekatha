from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import TrackProcessingStatus
from apps.catalog.tests.factories import AudioTrackFactory
from apps.playlists.admin import PlaylistAdmin, PlaylistItemInline
from apps.playlists.models import Playlist, PlaylistItem
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory

pytestmark = pytest.mark.django_db


def test_playlist_admin_has_requested_columns_sections_actions_and_track_fields():
    model_admin = admin.site._registry[Playlist]

    assert isinstance(model_admin, PlaylistAdmin)
    assert model_admin.list_display == (
        "cover_thumbnail",
        "title_ne",
        "playlist_type",
        "visibility",
        "owner",
        "track_count",
        "total_duration",
        "is_featured",
        "is_published",
        "updated_at",
    )
    assert tuple(name for name, _ in model_admin.fieldsets)[:7] == (
        "Basic information",
        "Cover image",
        "Description",
        "Visibility",
        "Featured status",
        "Publication settings",
        "Ordered tracks",
    )
    assert {
        "play_playlist_preview",
        "duplicate_selected",
        "publish_selected",
        "unpublish_selected",
        "feature_selected",
        "unfeature_selected",
        "add_to_new_playlists_homepage",
        "recalculate_positions",
        "remove_unavailable_tracks",
    } == set(model_admin.actions)
    assert PlaylistItemInline.autocomplete_fields == ("track",)
    assert PlaylistItemInline.ordering_field == "position"
    assert PlaylistItemInline.hide_ordering_field is False
    assert "is_featured" not in model_admin.readonly_fields
    assert {
        "track_duration",
        "track_narrator",
        "track_author",
        "processing_status",
    } <= set(PlaylistItemInline.readonly_fields)


def test_playlist_admin_annotates_count_and_duration(rf):
    playlist = PlaylistFactory(editorial=True)
    PlaylistItemFactory(
        playlist=playlist,
        position=1,
        track__duration_seconds=125,
    )
    PlaylistItemFactory(
        playlist=playlist,
        position=2,
        track__duration_seconds=65,
    )
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    model_admin = admin.site._registry[Playlist]

    result = model_admin.get_queryset(request).get(pk=playlist.pk)

    assert model_admin.track_count(result) == 2
    assert model_admin.total_duration(result) == "3:10"


def test_playlist_admin_hides_user_playlists_and_allows_confirmed_deletion(rf):
    user_playlist = PlaylistFactory()
    editorial = PlaylistFactory(editorial=True)
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    model_admin = admin.site._registry[Playlist]

    visible_ids = set(model_admin.get_queryset(request).values_list("id", flat=True))

    assert editorial.id in visible_ids
    assert user_playlist.id not in visible_ids
    assert model_admin.has_delete_permission(request, editorial) is True


def test_playlist_item_admin_hides_items_from_user_playlists(rf):
    user_item = PlaylistItemFactory(playlist=PlaylistFactory())
    editorial_item = PlaylistItemFactory(playlist=PlaylistFactory(editorial=True))
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    model_admin = admin.site._registry[PlaylistItem]

    visible_ids = set(model_admin.get_queryset(request).values_list("id", flat=True))

    assert editorial_item.id in visible_ids
    assert user_item.id not in visible_ids


def test_large_playlist_uses_bounded_relationship_interface(rf):
    playlist = PlaylistFactory(editorial=True)
    model_admin = admin.site._registry[Playlist]
    playlist._track_count = model_admin.inline_track_limit + 1
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)

    assert model_admin.get_inline_instances(request, playlist) == []
    assert "Inline hidden" in str(model_admin.ordered_tracks_link(playlist))


def test_unfold_drag_markup_keeps_visible_keyboard_position_input(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    playlist = PlaylistFactory(editorial=True)
    PlaylistItemFactory(playlist=playlist, position=1)
    client.force_login(user)

    response = client.get(
        reverse("admin:playlists_playlist_change", args=(playlist.pk,))
    )

    assert response.status_code == 200
    assert b'data-ordering-field="position"' in response.content
    assert b"drag_indicator" in response.content
    assert b'name="items-0-position"' in response.content


def test_playlist_preview_is_lazy_and_follows_item_position(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    playlist = PlaylistFactory(editorial=True)
    second = PlaylistItemFactory(
        playlist=playlist,
        position=2,
        track__stream_file_low="processed/audio/second-low.mp3",
    )
    first = PlaylistItemFactory(
        playlist=playlist,
        position=1,
        track__stream_file_high="processed/audio/first-high.mp3",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.playlists.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    response = client.get(
        reverse("admin:playlists_playlist_change", args=(playlist.pk,))
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert content.index(first.track.title_ne) < content.index(second.track.title_ne)
    assert "data-album-play-all" in content
    deliver.assert_not_called()


def test_publication_readiness_identifies_unready_tracks():
    playlist = PlaylistFactory(editorial=True, is_published=False)
    PlaylistItemFactory(
        playlist=playlist,
        position=1,
        track__is_published=False,
        track__published_at=None,
        track__processing_status=TrackProcessingStatus.PROCESSING,
    )
    model_admin = admin.site._registry[Playlist]

    assert "Blocked" in model_admin.publication_readiness(playlist)


def test_inline_reorder_delegates_to_transactional_service(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    playlist = PlaylistFactory(editorial=True)
    first = PlaylistItemFactory(playlist=playlist, position=1)
    second = PlaylistItemFactory(playlist=playlist, position=2)
    client.force_login(user)

    response = client.post(
        reverse("admin:playlists_playlist_change", args=(playlist.pk,)),
        {
            "title_ne": playlist.title_ne,
            "title_en": playlist.title_en,
            "playlist_type": playlist.playlist_type,
            "owner": "",
            "description_ne": playlist.description_ne,
            "description_en": playlist.description_en,
            "visibility": playlist.visibility,
            "items-TOTAL_FORMS": "3",
            "items-INITIAL_FORMS": "2",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": str(first.pk),
            "items-0-playlist": str(playlist.pk),
            "items-0-track": str(first.track_id),
            "items-0-position": "2",
            "items-1-id": str(second.pk),
            "items-1-playlist": str(playlist.pk),
            "items-1-track": str(second.track_id),
            "items-1-position": "1",
            "items-2-id": "",
            "items-2-playlist": str(playlist.pk),
            "items-2-track": "",
            "items-2-position": "",
            "_save": "Save",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert any(
        "changed successfully" in str(message).lower()
        for message in response.context["messages"]
    )
    assert list(
        playlist.items.order_by("position").values_list("track_id", flat=True)
    ) == [second.track_id, first.track_id]


def test_inline_rejects_duplicate_server_positions_without_mutation(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    playlist = PlaylistFactory(editorial=True)
    first = PlaylistItemFactory(playlist=playlist, position=1)
    second = PlaylistItemFactory(playlist=playlist, position=2)
    client.force_login(user)

    response = client.post(
        reverse("admin:playlists_playlist_change", args=(playlist.pk,)),
        {
            "title_ne": playlist.title_ne,
            "title_en": playlist.title_en,
            "playlist_type": playlist.playlist_type,
            "owner": "",
            "description_ne": playlist.description_ne,
            "description_en": playlist.description_en,
            "visibility": playlist.visibility,
            "items-TOTAL_FORMS": "2",
            "items-INITIAL_FORMS": "2",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": str(first.pk),
            "items-0-playlist": str(playlist.pk),
            "items-0-track": str(first.track_id),
            "items-0-position": "1",
            "items-1-id": str(second.pk),
            "items-1-playlist": str(playlist.pk),
            "items-1-track": str(second.track_id),
            "items-1-position": "1",
            "_save": "Save",
        },
    )

    assert response.status_code == 200
    assert b"unique integer position" in response.content
    assert list(playlist.items.values_list("position", flat=True)) == [1, 2]


def test_preview_delivery_rejects_track_outside_playlist(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    playlist = PlaylistFactory(editorial=True)
    unrelated = AudioTrackFactory(stream_file_low="processed/audio/unrelated-low.mp3")
    deliver = Mock()
    monkeypatch.setattr(
        "apps.playlists.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    response = client.get(
        reverse(
            "admin:playlists_playlist_preview_delivery",
            kwargs={
                "object_id": playlist.pk,
                "track_id": unrelated.pk,
                "quality": "low",
            },
        )
    )

    assert response.status_code == 404
    deliver.assert_not_called()
