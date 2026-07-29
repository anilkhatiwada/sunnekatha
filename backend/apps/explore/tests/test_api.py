from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import TrackProcessingStatus
from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.models import PlaylistType, PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory
from apps.taxonomy.tests.factories import GenreFactory, LanguageFactory, MoodFactory

pytestmark = pytest.mark.django_db


def section_by_id(response, identifier):
    return next(
        section for section in response.data["sections"] if section["id"] == identifier
    )


def test_explore_aggregate_matches_frontend_sections_and_uses_compact_payloads():
    genre = GenreFactory(is_active=True)
    mood = MoodFactory(is_active=True)
    track = AudioTrackFactory(
        work__content_type="poem",
        work__genres=[genre],
        work__moods=[mood],
        play_count_cache=50,
    )
    playlist = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_featured=True,
        is_published=True,
    )
    PlaylistItemFactory(playlist=playlist, track=track, position=1, added_by=None)
    AlbumFactory(is_featured=True, is_published=True)

    response = APIClient().get(reverse("explore:detail"))

    assert response.status_code == status.HTTP_200_OK
    assert [section["id"] for section in response.data["sections"]] == [
        "content-types",
        "genres",
        "moods",
        "featured-playlists",
        "featured-albums",
        "popular-authors",
        "popular-narrators",
        "new-releases",
    ]
    assert all(section["title"] for section in response.data["sections"])
    poem = next(
        item
        for item in section_by_id(response, "content-types")["items"]
        if item["slug"] == "poem"
    )
    assert poem["trackCount"] == 1
    assert section_by_id(response, "genres")["items"][0]["slug"] == genre.slug
    assert section_by_id(response, "moods")["items"][0]["slug"] == mood.slug
    release = section_by_id(response, "new-releases")["items"][0]
    assert release["id"] == str(track.id)
    assert "transcript" not in release
    assert "audio_master_file" not in release


def test_explore_aggregate_excludes_private_and_unpublished_content():
    unpublished = AudioTrackFactory(is_published=False, published_at=None)
    future = AudioTrackFactory(published_at=timezone.now() + timedelta(days=1))
    failed = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.FAILED,
    )
    PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PRIVATE,
        is_featured=True,
        is_published=True,
    )
    AlbumFactory(is_featured=True, is_published=False)

    response = APIClient().get(reverse("explore:detail"))

    ids = {item["id"] for item in section_by_id(response, "new-releases")["items"]}
    assert ids.isdisjoint({str(unpublished.id), str(future.id), str(failed.id)})
    assert section_by_id(response, "featured-playlists")["items"] == []
    assert section_by_id(response, "featured-albums")["items"] == []


def test_explore_track_list_is_paginated_and_defaults_to_newest_first():
    old = AudioTrackFactory(published_at=timezone.now() - timedelta(days=1))
    new = AudioTrackFactory(published_at=timezone.now())

    response = APIClient().get(
        reverse("explore:track-list"),
        {"pageSize": 1},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == str(new.id)
    assert response.data["next"]
    assert str(old.id) not in {item["id"] for item in response.data["results"]}


def test_explore_track_filters_support_the_requested_parameters():
    genre = GenreFactory()
    mood = MoodFactory()
    author = AuthorFactory()
    narrator = NarratorFactory()
    language = LanguageFactory(slug="en")
    matching = AudioTrackFactory(
        work__content_type="poem",
        work__author=author,
        work__genres=[genre],
        work__moods=[mood],
        narrator=narrator,
        language=language,
        is_premium=True,
        is_explicit=False,
    )
    AudioTrackFactory()

    response = APIClient().get(
        reverse("explore:track-list"),
        {
            "content_type": "poem",
            "genre": genre.slug,
            "mood": mood.slug,
            "language": "en",
            "author": author.slug,
            "narrator": narrator.slug,
            "premium": "true",
            "explicit": "false",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in response.data["results"]] == [str(matching.id)]


def test_explore_track_list_accepts_frontend_content_type_alias_and_ordering():
    less_popular = AudioTrackFactory(work__content_type="story", play_count_cache=1)
    more_popular = AudioTrackFactory(work__content_type="story", play_count_cache=100)
    AudioTrackFactory(work__content_type="poem", play_count_cache=1000)

    response = APIClient().get(
        reverse("explore:track-list"),
        {"contentType": "story", "ordering": "-play_count_cache"},
    )

    assert [item["id"] for item in response.data["results"]] == [
        str(more_popular.id),
        str(less_popular.id),
    ]


def test_explore_aggregate_sections_are_bounded():
    AudioTrackFactory.create_batch(8)
    GenreFactory.create_batch(14)
    MoodFactory.create_batch(14)

    response = APIClient().get(reverse("explore:detail"))

    for section in response.data["sections"]:
        limit = 12 if section["id"] in {"genres", "moods"} else 6
        assert len(section["items"]) <= limit
