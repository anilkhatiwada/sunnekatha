from datetime import timedelta

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import TrackProcessingStatus
from apps.catalog.tests.factories import AudioTrackFactory
from apps.taxonomy.tests.factories import GenreFactory, MoodFactory

pytestmark = pytest.mark.django_db


def test_track_list_only_returns_ready_currently_published_tracks():
    visible = AudioTrackFactory()
    AudioTrackFactory(is_published=False, published_at=None)
    AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
    )
    AudioTrackFactory(published_at=timezone.now() + timedelta(days=1))

    response = APIClient().get(reverse("catalog:track-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(visible.id)


def test_track_detail_hides_unpublished_track():
    draft = AudioTrackFactory(is_published=False, published_at=None)

    response = APIClient().get(
        reverse("catalog:track-detail", kwargs={"slug": draft.slug})
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_track_filters_and_ordering():
    genre = GenreFactory(slug="poetry")
    mood = MoodFactory(slug="calm")
    expected = AudioTrackFactory(
        work__content_type="poem",
        work__genres=[genre],
        work__moods=[mood],
        is_featured=True,
        play_count_cache=100,
    )
    AudioTrackFactory(play_count_cache=10)

    response = APIClient().get(
        reverse("catalog:track-list"),
        {
            "contentType": "poem",
            "author": expected.work.author.slug,
            "narrator": expected.narrator.slug,
            "genre": genre.slug,
            "mood": mood.slug,
            "language": expected.language.slug,
            "featured": "true",
            "ordering": "-play_count_cache",
        },
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(expected.id)


@pytest.mark.parametrize(
    ("url_name", "kwargs"),
    [
        ("catalog:tracks-by-content-type", {"content_type": "poem"}),
        ("catalog:tracks-by-author", {"slug": "author-slug"}),
        ("catalog:tracks-by-narrator", {"slug": "narrator-slug"}),
        ("catalog:tracks-by-genre", {"slug": "poetry"}),
        ("catalog:tracks-by-mood", {"slug": "calm"}),
    ],
)
def test_relation_endpoints(url_name, kwargs):
    genre = GenreFactory(slug="poetry")
    mood = MoodFactory(slug="calm")
    expected = AudioTrackFactory(
        work__content_type="poem",
        work__author__slug="author-slug",
        work__genres=[genre],
        work__moods=[mood],
        narrator__slug="narrator-slug",
    )
    AudioTrackFactory()

    response = APIClient().get(reverse(url_name, kwargs=kwargs))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(expected.id)


def test_featured_trending_and_recent_endpoints_have_expected_order():
    older = AudioTrackFactory(
        is_featured=True,
        play_count_cache=500,
        published_at=timezone.now() - timedelta(days=2),
    )
    newer = AudioTrackFactory(
        is_featured=True,
        play_count_cache=5,
        published_at=timezone.now() - timedelta(days=1),
    )

    featured = APIClient().get(reverse("catalog:track-featured"))
    trending = APIClient().get(reverse("catalog:track-trending"))
    recent = APIClient().get(reverse("catalog:track-recent"))

    assert featured.data["count"] == 2
    assert trending.data["results"][0]["id"] == str(older.id)
    assert recent.data["results"][0]["id"] == str(newer.id)


def test_related_tracks_excludes_source_and_matches_shared_taxonomy():
    genre = GenreFactory()
    source = AudioTrackFactory(work__genres=[genre])
    related = AudioTrackFactory(work__genres=[genre])
    AudioTrackFactory(work__content_type="drama")

    response = APIClient().get(
        reverse("catalog:track-related", kwargs={"slug": source.slug})
    )

    ids = {item["id"] for item in response.data["results"]}
    assert str(source.id) not in ids
    assert str(related.id) in ids


def test_related_tracks_returns_not_found_for_unknown_source():
    response = APIClient().get(
        reverse("catalog:track-related", kwargs={"slug": "missing"})
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_track_list_uses_bounded_queries(django_assert_num_queries):
    AudioTrackFactory.create_batch(3)

    with django_assert_num_queries(4):
        response = APIClient().get(reverse("catalog:track-list"))

    assert response.status_code == status.HTTP_200_OK


def test_track_list_omits_detail_only_fields():
    AudioTrackFactory(
        description_ne="लामो विवरण",
        description_en="Long description",
        transcript="पूर्ण प्रतिलिपि",
    )
    item = APIClient().get(reverse("catalog:track-list")).data["results"][0]

    assert "description" not in item
    assert "descriptionEnglish" not in item
    assert "transcript" not in item
    assert "waveform" not in item


def test_track_detail_has_bounded_queries():
    cache.clear()
    track = AudioTrackFactory(
        work__genres=GenreFactory.create_batch(2),
        work__moods=MoodFactory.create_batch(2),
    )

    with CaptureQueriesContext(connection) as queries:
        response = APIClient().get(
            reverse("catalog:track-detail", kwargs={"slug": track.slug})
        )

    assert response.status_code == status.HTTP_200_OK
    assert "transcript" in response.data
    assert len(queries) <= 3
