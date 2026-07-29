from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
)

from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import AlbumAdmin, AlbumTrackInline
from apps.catalog.models import Album
from apps.catalog.services import EditorialService
from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.taxonomy.tests.factories import GenreFactory, MoodFactory

pytestmark = pytest.mark.django_db


def test_album_admin_has_requested_columns_filters_actions_and_preview_fields():
    model_admin = admin.site._registry[Album]

    assert isinstance(model_admin, AlbumAdmin)
    assert model_admin.list_display == (
        "cover_thumbnail",
        "title_ne",
        "title_en",
        "author",
        "album_type",
        "track_count",
        "total_duration",
        "is_featured",
        "is_published",
        "release_date",
    )
    assert model_admin.list_filter == (
        ("album_type", ChoicesDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("is_featured", BooleanRadioFilter),
        ("is_published", BooleanRadioFilter),
        ("release_date", RangeDateFilter),
    )
    assert model_admin.inlines == (AlbumTrackInline,)
    assert "duplicate_selected" in model_admin.actions
    assert {
        "cover_preview",
        "play_all_preview",
        "public_page_preview",
        "track_relationship_link",
    } <= set(model_admin.readonly_fields)


def test_album_admin_annotates_track_count_and_total_duration(rf):
    album = AlbumFactory()
    AudioTrackFactory(album=album, duration_seconds=125)
    AudioTrackFactory(album=album, duration_seconds=3600)
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    model_admin = admin.site._registry[Album]

    result = model_admin.get_queryset(request).get(pk=album.pk)

    assert model_admin.track_count(result) == 2
    assert model_admin.total_duration(result) == "1:02:05"


def test_album_inline_order_is_stable_and_large_albums_use_relationship_link(rf):
    model_admin = admin.site._registry[Album]
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    album = AlbumFactory()
    album._track_count = model_admin.inline_track_limit + 1

    assert AlbumTrackInline.ordering == (
        "track_number",
        "chapter_number",
        "title_ne",
        "id",
    )
    assert model_admin.get_inline_instances(request, album) == []
    assert "Inline hidden" in str(model_admin.track_relationship_link(album))


def test_album_play_all_manifest_is_stable_bounded_and_does_not_sign():
    album = AlbumFactory()
    later = AudioTrackFactory(
        album=album,
        track_number=2,
        stream_file_low="processed/audio/later-low.mp3",
    )
    first = AudioTrackFactory(
        album=album,
        track_number=1,
        stream_file_high="processed/audio/first-high.mp3",
    )
    model_admin = admin.site._registry[Album]

    tracks, truncated = model_admin._play_all_tracks(album)
    html = str(model_admin.play_all_preview(album))

    assert [track.pk for track in tracks] == [first.pk, later.pk]
    assert truncated is False
    assert "data-album-play-all" in html
    assert "play-all" in html
    assert "https://audio" not in html


def test_album_change_page_does_not_request_cloudfront_url(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    album = AlbumFactory()
    AudioTrackFactory(
        album=album,
        stream_file_low="processed/audio/preview-low.mp3",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    response = client.get(reverse("admin:catalog_album_change", args=(album.pk,)))

    assert response.status_code == 200
    assert b"Play all" in response.content
    deliver.assert_not_called()


def test_album_play_all_delivery_uses_cloudfront_service(client, monkeypatch):
    user = UserFactory(is_staff=True, is_superuser=True)
    album = AlbumFactory()
    track = AudioTrackFactory(
        album=album,
        stream_file_low="processed/audio/preview-low.mp3",
    )
    deliver = Mock(
        return_value={
            "quality": "low",
            "url": "https://media.example.test/free/preview-low.mp3",
            "expiresAt": None,
        }
    )
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    response = client.get(
        reverse(
            "admin:catalog_album_play_all_delivery",
            kwargs={
                "object_id": album.pk,
                "track_id": track.pk,
                "quality": "low",
            },
        )
    )

    assert response.status_code == 200
    assert response.json()["url"].startswith("https://media.example.test/")
    assert response["Cache-Control"].startswith("private, no-store")
    deliver.assert_called_once_with(track, quality="low", request=response.wsgi_request)


def test_album_play_all_delivery_requires_track_permission(client, monkeypatch):
    album = AlbumFactory()
    track = AudioTrackFactory(
        album=album,
        stream_file_low="processed/audio/preview-low.mp3",
    )
    editor = UserFactory(is_staff=True)
    editor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="catalog",
            codename="view_album",
        )
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(editor)

    response = client.get(
        reverse(
            "admin:catalog_album_play_all_delivery",
            kwargs={
                "object_id": album.pk,
                "track_id": track.pk,
                "quality": "low",
            },
        )
    )

    assert response.status_code == 403
    deliver.assert_not_called()


def test_duplicate_album_copies_metadata_taxonomy_but_not_tracks():
    genre = GenreFactory()
    mood = MoodFactory()
    album = AlbumFactory(
        genres=(genre,),
        moods=(mood,),
        is_featured=True,
        is_published=True,
    )
    AudioTrackFactory(album=album)

    duplicate = EditorialService.duplicate_album(
        album,
        actor=UserFactory(is_staff=True, is_superuser=True),
    )

    assert duplicate.pk != album.pk
    assert duplicate.title_ne == album.title_ne
    assert duplicate.is_featured is False
    assert duplicate.is_published is False
    assert list(duplicate.genres.all()) == [genre]
    assert list(duplicate.moods.all()) == [mood]
    assert duplicate.audio_tracks.count() == 0


def test_published_album_has_named_public_preview():
    album = AlbumFactory(is_published=True)
    model_admin = admin.site._registry[Album]

    assert reverse("catalog:album-detail", kwargs={"slug": album.slug}) in str(
        model_admin.public_page_preview(album)
    )
