import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.library.progress import listening_progress_service
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.models import PlaylistType, PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory
from apps.taxonomy.tests.factories import MoodFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_home_cache():
    cache.clear()
    yield
    cache.clear()


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def seed_public_home():
    playlist = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_featured=True,
        is_published=True,
    )
    PlaylistItemFactory(playlist=playlist, position=1)
    AudioTrackFactory.create_batch(7)
    NarratorFactory(is_featured=True, follower_count_cache=500)
    MoodFactory(is_active=True)
    AlbumFactory(is_featured=True, is_published=True)
    return playlist


def section_by_id(response, identifier):
    return next(
        section for section in response.data["sections"] if section["id"] == identifier
    )


def test_anonymous_home_returns_all_public_sections_without_personal_data():
    playlist = seed_public_home()

    response = APIClient().get(reverse("home:detail"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["hero"]["id"] == "hero"
    assert response.data["hero"]["content"]["id"] == str(playlist.id)
    identifiers = [section["id"] for section in response.data["sections"]]
    assert identifiers == [
        "featured-playlists",
        "trending-tracks",
        "recently-added",
        "popular-authors",
        "popular-narrators",
        "mood-collections",
        "featured-albums",
    ]
    assert "continue-listening" not in identifiers
    assert all(section["title"] for section in response.data["sections"])


def test_authenticated_home_adds_only_the_current_users_continue_listening():
    seed_public_home()
    user = UserFactory()
    own_track = AudioTrackFactory(duration_seconds=100)
    other_track = AudioTrackFactory(duration_seconds=100)
    listening_progress_service.update(
        user=user,
        track=own_track,
        position_seconds=25,
        duration_seconds=100,
    )
    listening_progress_service.update(
        user=UserFactory(),
        track=other_track,
        position_seconds=50,
        duration_seconds=100,
    )

    response = authenticated_client(user).get(reverse("home:detail"))

    section = section_by_id(response, "continue-listening")
    assert section["title"] == "अहिले सुन्दै हुनुहुन्छ"
    assert [item["track"]["id"] for item in section["items"]] == [str(own_track.id)]


def test_public_cache_never_leaks_personalized_sections():
    seed_public_home()
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=100)
    listening_progress_service.update(
        user=user,
        track=track,
        position_seconds=20,
        duration_seconds=100,
    )

    authenticated = authenticated_client(user).get(reverse("home:detail"))
    anonymous = APIClient().get(reverse("home:detail"))

    assert section_by_id(authenticated, "continue-listening")
    assert "continue-listening" not in [
        section["id"] for section in anonymous.data["sections"]
    ]


def test_home_sections_have_bounded_payloads():
    seed_public_home()

    response = APIClient().get(reverse("home:detail"))

    for section in response.data["sections"]:
        expected_limit = 4 if section["id"] == "mood-collections" else 6
        assert len(section["items"]) <= expected_limit


def test_public_home_payload_is_reused_from_cache(django_assert_num_queries):
    seed_public_home()
    first = APIClient().get(reverse("home:detail"))
    assert first.status_code == status.HTTP_200_OK

    with django_assert_num_queries(0):
        second = APIClient().get(reverse("home:detail"))

    assert second.data == first.data


def test_uncached_public_home_has_bounded_queries(django_assert_num_queries):
    seed_public_home()

    with django_assert_num_queries(12):
        response = APIClient().get(reverse("home:detail"))

    assert response.status_code == status.HTTP_200_OK


def test_authenticated_personalization_queries_remain_bounded(
    django_assert_num_queries,
):
    seed_public_home()
    user = UserFactory()
    listening_progress_service.update(
        user=user,
        track=AudioTrackFactory(duration_seconds=100),
        position_seconds=10,
        duration_seconds=100,
    )
    APIClient().get(reverse("home:detail"))

    with django_assert_num_queries(3):
        response = authenticated_client(user).get(reverse("home:detail"))

    assert section_by_id(response, "continue-listening")["items"]
