import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.common.cache import public_cache_keys
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.models import PlaylistType, PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory
from apps.taxonomy.tests.factories import GenreFactory, MoodFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_public_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.parametrize(
    ("url_name", "factory"),
    (
        ("authors:featured", lambda: AuthorFactory(is_featured=True)),
        ("narrators:featured", lambda: NarratorFactory(is_featured=True)),
        ("taxonomy:genre-list", lambda: GenreFactory(is_active=True)),
        ("taxonomy:mood-list", lambda: MoodFactory(is_active=True)),
    ),
)
def test_public_lists_are_reused_from_cache(
    url_name,
    factory,
    django_assert_num_queries,
):
    factory()
    client = APIClient()
    first = client.get(reverse(url_name))
    assert first.status_code == 200

    with django_assert_num_queries(0):
        second = client.get(reverse(url_name))
    assert second.data == first.data


def test_featured_list_cache_is_invalidated_after_model_change():
    author = AuthorFactory(is_featured=True)
    client = APIClient()
    url = reverse("authors:featured")
    assert client.get(url).data["count"] == 1

    author.is_featured = False
    author.save(update_fields=("is_featured", "updated_at"))

    assert client.get(url).data["count"] == 0


def test_featured_playlists_are_reused_from_cache(django_assert_num_queries):
    playlist = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_featured=True,
        is_published=True,
    )
    PlaylistItemFactory(playlist=playlist, position=1)
    client = APIClient()
    url = reverse("playlists:featured")
    first = client.get(url)
    assert first.status_code == 200

    with django_assert_num_queries(0):
        second = client.get(url)
    assert second.data == first.data


def test_public_track_metadata_is_cached_and_invalidated(django_assert_num_queries):
    track = AudioTrackFactory(title_ne="पहिलो शीर्षक")
    client = APIClient()
    url = reverse("catalog:track-detail", args=[track.slug])
    assert client.get(url).data["title"] == "पहिलो शीर्षक"

    with django_assert_num_queries(0):
        assert client.get(url).data["title"] == "पहिलो शीर्षक"

    track.title_ne = "परिवर्तित शीर्षक"
    track.save(update_fields=("title_ne", "updated_at"))
    assert client.get(url).data["title"] == "परिवर्तित शीर्षक"


def test_player_and_detailed_track_payloads_use_separate_keys():
    track = AudioTrackFactory()
    client = APIClient()
    detail = client.get(reverse("catalog:track-detail", args=[track.slug]))
    player = client.get(reverse("catalog:track-player", args=[track.slug]))

    assert "author" in detail.data
    assert "media" in player.data
    assert "media" not in detail.data


def test_related_author_change_invalidates_nested_track_metadata():
    track = AudioTrackFactory()
    client = APIClient()
    url = reverse("catalog:track-detail", args=[track.slug])
    assert client.get(url).data["author"]["name"] == track.work.author.name_ne

    track.work.author.name_ne = "परिवर्तित लेखक"
    track.work.author.save(update_fields=("name_ne", "updated_at"))

    assert client.get(url).data["author"]["name"] == "परिवर्तित लेखक"


def test_public_playlist_detail_is_cached_and_item_changes_invalidate_it(
    django_assert_num_queries,
):
    playlist = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_published=True,
    )
    first_item = PlaylistItemFactory(playlist=playlist, position=1)
    client = APIClient()
    url = reverse("playlists:detail", args=[playlist.slug])
    assert client.get(url).data["trackCount"] == 1

    with django_assert_num_queries(0):
        assert client.get(url).data["tracks"][0]["id"] == str(first_item.track_id)

    PlaylistItemFactory(playlist=playlist, position=2)
    assert client.get(url).data["trackCount"] == 2


def test_private_playlist_detail_is_never_put_in_public_cache():
    owner = UserFactory()
    playlist = PlaylistFactory(
        owner=owner,
        playlist_type=PlaylistType.USER,
        visibility=PlaylistVisibility.PRIVATE,
        is_published=True,
    )
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get(reverse("playlists:detail", args=[playlist.slug]))
    assert response.status_code == 200

    key = public_cache_keys.key(
        "playlist-detail",
        identifier=playlist.slug,
        host="testserver",
    )
    assert cache.get(key) is None


def test_query_parameters_use_distinct_taxonomy_cache_keys():
    GenreFactory(name_ne="कविता", is_active=True)
    GenreFactory(name_ne="कथा", is_active=False)
    client = APIClient()
    url = reverse("taxonomy:genre-list")

    active = client.get(url, {"active": "true"})
    inactive = client.get(url, {"active": "false"})

    assert active.data != inactive.data
