import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import (
    FavoriteTrack,
    FollowedAuthor,
    FollowedNarrator,
    SavedPlaylist,
)
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.models import PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory

pytestmark = pytest.mark.django_db


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.parametrize(
    ("url_name", "target_factory", "model", "target_field", "state_field"),
    [
        (
            "library:favorite-track",
            AudioTrackFactory,
            FavoriteTrack,
            "track",
            "is_favorited",
        ),
        (
            "library:save-playlist",
            lambda: PlaylistFactory(editorial=True),
            SavedPlaylist,
            "playlist",
            "is_playlist_saved",
        ),
        (
            "library:follow-author",
            AuthorFactory,
            FollowedAuthor,
            "author",
            "is_author_followed",
        ),
        (
            "library:follow-narrator",
            NarratorFactory,
            FollowedNarrator,
            "narrator",
            "is_narrator_followed",
        ),
    ],
)
def test_relationship_operations_are_idempotent(
    url_name,
    target_factory,
    model,
    target_field,
    state_field,
):
    user = UserFactory()
    target = target_factory()
    client = client_for(user)
    url = reverse(url_name, kwargs={"target_id": target.id})

    first = client.post(url)
    second = client.put(url)

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert first.data == {"id": str(target.id), state_field: True}
    assert model.objects.filter(user=user, **{target_field: target}).count() == 1

    removed = client.delete(url)
    removed_again = client.delete(url)

    assert removed.data == {"id": str(target.id), state_field: False}
    assert removed_again.status_code == status.HTTP_200_OK
    assert not model.objects.filter(user=user, **{target_field: target}).exists()


@pytest.mark.parametrize(
    "url_name",
    [
        "library:favorite-track-list",
        "library:saved-playlist-list",
        "library:followed-author-list",
        "library:followed-narrator-list",
    ],
)
def test_library_lists_require_authentication(url_name):
    response = APIClient().get(reverse(url_name))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_favorite_track_list_is_user_scoped_and_has_flag():
    user = UserFactory()
    favorite = FavoriteTrack.objects.create(user=user, track=AudioTrackFactory())
    FavoriteTrack.objects.create(user=UserFactory(), track=AudioTrackFactory())

    response = client_for(user).get(reverse("library:favorite-track-list"))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(favorite.track_id)
    assert response.data["results"][0]["is_favorited"] is True


def test_saved_playlist_list_respects_privacy_and_has_flag():
    user = UserFactory()
    own_private = PlaylistFactory(
        owner=user,
        visibility=PlaylistVisibility.PRIVATE,
    )
    now_private = PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)
    SavedPlaylist.objects.create(user=user, playlist=own_private)
    SavedPlaylist.objects.create(user=user, playlist=now_private)

    response = client_for(user).get(reverse("library:saved-playlist-list"))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(own_private.id)
    assert response.data["results"][0]["is_playlist_saved"] is True


def test_followed_lists_are_user_scoped_and_have_flags():
    user = UserFactory()
    author = AuthorFactory()
    narrator = NarratorFactory()
    FollowedAuthor.objects.create(user=user, author=author)
    FollowedNarrator.objects.create(user=user, narrator=narrator)

    authors = client_for(user).get(reverse("library:followed-author-list"))
    narrators = client_for(user).get(reverse("library:followed-narrator-list"))

    assert authors.data["results"][0]["is_author_followed"] is True
    assert narrators.data["results"][0]["is_narrator_followed"] is True


def test_narrator_follow_count_cache_changes_once_per_relationship():
    user = UserFactory()
    narrator = NarratorFactory(follower_count_cache=7)
    url = reverse("library:follow-narrator", kwargs={"target_id": narrator.id})
    client = client_for(user)

    client.post(url)
    client.post(url)
    narrator.refresh_from_db()
    assert narrator.follower_count_cache == 8

    client.delete(url)
    client.delete(url)
    narrator.refresh_from_db()
    assert narrator.follower_count_cache == 7


def test_cannot_favorite_unpublished_track_or_save_inaccessible_playlist():
    user = UserFactory()
    track = AudioTrackFactory(is_published=False, published_at=None)
    playlist = PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)
    client = client_for(user)

    track_response = client.post(
        reverse("library:favorite-track", kwargs={"target_id": track.id})
    )
    playlist_response = client.post(
        reverse("library:save-playlist", kwargs={"target_id": playlist.id})
    )

    assert track_response.status_code == status.HTTP_404_NOT_FOUND
    assert playlist_response.status_code == status.HTTP_404_NOT_FOUND


def test_favorite_track_list_has_bounded_queries(django_assert_num_queries):
    user = UserFactory()
    for _ in range(3):
        FavoriteTrack.objects.create(user=user, track=AudioTrackFactory())

    with django_assert_num_queries(4):
        response = client_for(user).get(reverse("library:favorite-track-list"))

    assert response.data["count"] == 3


def test_saved_playlist_list_has_bounded_queries(django_assert_num_queries):
    user = UserFactory()
    for _ in range(3):
        playlist = PlaylistFactory(editorial=True)
        PlaylistItemFactory(playlist=playlist, position=1)
        SavedPlaylist.objects.create(user=user, playlist=playlist)

    with django_assert_num_queries(2):
        response = client_for(user).get(reverse("library:saved-playlist-list"))

    assert response.data["count"] == 3


@pytest.mark.parametrize(
    ("url_name", "relationship_model", "target_factory", "target_field"),
    [
        (
            "library:followed-author-list",
            FollowedAuthor,
            AuthorFactory,
            "author",
        ),
        (
            "library:followed-narrator-list",
            FollowedNarrator,
            NarratorFactory,
            "narrator",
        ),
    ],
)
def test_followed_people_lists_have_bounded_queries(
    url_name,
    relationship_model,
    target_factory,
    target_field,
):
    user = UserFactory()
    for _ in range(5):
        relationship_model.objects.create(
            user=user,
            **{target_field: target_factory()},
        )

    with CaptureQueriesContext(connection) as queries:
        response = client_for(user).get(reverse(url_name))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 5
    assert len(queries) <= 3
