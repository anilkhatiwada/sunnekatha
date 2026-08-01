import pytest
from django.db import connection
from django.db.models import CharField
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.models import PlaylistType, PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory
from apps.search.models import SearchAlias, SearchEntityType
from apps.taxonomy.tests.factories import GenreFactory, MoodFactory

pytestmark = pytest.mark.django_db


def test_postgresql_unaccent_lookup_is_registered():
    assert CharField().get_transform("unaccent") is not None


def test_grouped_search_matches_nepali_across_supported_entities():
    author = AuthorFactory(name_ne="पारिजात")
    narrator = NarratorFactory(name_ne="अच्युत घिमिरे")
    genre = GenreFactory(name_ne="कविता")
    mood = MoodFactory(name_ne="शान्ति")
    track = AudioTrackFactory(
        title_ne="वर्षाको साँझ",
        work__title_ne="शिरीषको फूल",
        work__author=author,
        work__genres=[genre],
        work__moods=[mood],
        narrator=narrator,
    )
    album = AlbumFactory(title_ne="वर्षाका स्वर")
    playlist = PlaylistFactory(
        owner=None,
        title_ne="वर्षा विशेष",
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_published=True,
    )

    response = APIClient().get(reverse("search:grouped"), {"q": "वर्षा"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["query"] == "वर्षा"
    assert [item["id"] for item in response.data["tracks"]] == [str(track.id)]
    assert [item["id"] for item in response.data["playlists"]] == [str(playlist.id)]
    assert [item["id"] for item in response.data["albums"]] == [str(album.id)]
    assert "literaryWorks" in response.data


def test_grouped_search_matches_english_names_and_partial_text():
    author = AuthorFactory(name_ne="लक्ष्मीप्रसाद देवकोटा", name_en="Laxmi Prasad Devkota")
    track = AudioTrackFactory(
        title_en="The Great Poet",
        description_en="A celebrated Nepali literary voice",
        work__author=author,
    )

    response = APIClient().get(reverse("search:grouped"), {"q": "Devkot"})

    assert [item["id"] for item in response.data["authors"]] == [str(author.id)]
    assert [item["id"] for item in response.data["tracks"]] == [str(track.id)]


def test_romanized_alias_matches_entity_and_related_tracks():
    author = AuthorFactory(name_ne="लेखनाथ पौड्याल", name_en="")
    track = AudioTrackFactory(work__author=author)
    SearchAlias.objects.create(
        entity_type=SearchEntityType.AUTHOR,
        object_id=author.id,
        alias="Kavi Shiromani",
    )

    response = APIClient().get(reverse("search:grouped"), {"q": "shirom"})

    assert [item["id"] for item in response.data["authors"]] == [str(author.id)]
    assert [item["id"] for item in response.data["tracks"]] == [str(track.id)]


def test_track_search_is_paginated_filtered_and_excludes_unpublished_tracks():
    poem = AudioTrackFactory(work__content_type="poem", title_en="Moon Song")
    AudioTrackFactory(work__content_type="story", title_en="Moon Story")
    hidden = AudioTrackFactory(
        work__content_type="poem",
        title_en="Moon Hidden",
        is_published=False,
        published_at=None,
    )

    response = APIClient().get(
        reverse("search:tracks"),
        {"q": "Moon", "content_type": "poem", "pageSize": 1},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert [item["id"] for item in response.data["results"]] == [str(poem.id)]
    assert str(hidden.id) not in {item["id"] for item in response.data["results"]}


def test_grouped_type_filter_returns_only_the_requested_group():
    AudioTrackFactory(title_ne="रातको कथा")
    GenreFactory(name_ne="कथा")

    response = APIClient().get(
        reverse("search:grouped"),
        {"q": "कथा", "type": "genres"},
    )

    assert response.data["genres"]
    for key in (
        "tracks",
        "literaryWorks",
        "playlists",
        "albums",
        "authors",
        "narrators",
        "moods",
    ):
        assert response.data[key] == []


def test_grouped_search_accepts_frontend_parameter_names():
    track = AudioTrackFactory(
        title_ne="फ्रन्टेन्ड खोज",
        work__content_type="story",
    )

    response = APIClient().get(
        reverse("search:grouped"),
        {
            "query": "फ्रन्टेन्ड",
            "resultType": "tracks",
            "contentType": "story",
        },
    )

    assert [item["id"] for item in response.data["tracks"]] == [str(track.id)]
    assert response.data["authors"] == []


def test_search_rejects_conflicting_parameter_aliases():
    response = APIClient().get(
        reverse("search:grouped"),
        {"q": "कथा", "query": "कविता"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "query" in response.data["errors"]


def test_autocomplete_returns_bounded_typed_suggestions():
    track = AudioTrackFactory(title_ne="मुनामदन")
    AuthorFactory(name_ne="मुनाका लेखक")

    response = APIClient().get(
        reverse("search:autocomplete"),
        {"q": "मुना"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) <= 10
    assert {
        "type",
        "id",
        "slug",
        "label",
        "labelEnglish",
    } <= response.data[0].keys()
    assert any(item["id"] == str(track.id) for item in response.data)


def test_empty_query_returns_empty_results_and_invalid_type_is_rejected():
    empty = APIClient().get(reverse("search:grouped"))
    invalid = APIClient().get(
        reverse("search:grouped"),
        {"q": "कथा", "type": "unknown"},
    )

    assert empty.status_code == status.HTTP_200_OK
    assert all(
        empty.data[key] == []
        for key in (
            "tracks",
            "literaryWorks",
            "playlists",
            "albums",
            "authors",
            "narrators",
            "genres",
            "moods",
        )
    )
    assert invalid.status_code == status.HTTP_400_BAD_REQUEST


def test_trending_search_placeholder_is_stable_and_nepali_aware():
    response = APIClient().get(reverse("search:trending"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["searches"]
    assert "प्रेमका कविता" in response.data["searches"]


def test_track_search_has_bounded_queries_for_multiple_nested_results():
    AudioTrackFactory.create_batch(6, title_ne="साझा खोज शीर्षक")

    with CaptureQueriesContext(connection) as queries:
        response = APIClient().get(
            reverse("search:tracks"),
            {"q": "साझा", "pageSize": 10},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 6
    assert len(queries) <= 6


def test_grouped_search_uses_compact_payloads_and_bounded_queries():
    track = AudioTrackFactory(
        title_ne="वर्षा कथा",
        description_ne="लामो ट्र्याक विवरण",
        transcript="पूर्ण प्रतिलिपि",
    )
    PlaylistFactory(
        owner=None,
        title_ne="वर्षा सङ्ग्रह",
        description_ne="लामो प्लेलिस्ट विवरण",
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
    )

    with CaptureQueriesContext(connection) as queries:
        response = APIClient().get(reverse("search:grouped"), {"q": "वर्षा"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["tracks"][0]["id"] == str(track.id)
    assert "transcript" not in response.data["tracks"][0]
    assert "description" not in response.data["tracks"][0]
    assert "tracks" not in response.data["playlists"][0]
    assert "description" not in response.data["playlists"][0]
    assert len(queries) <= 20
