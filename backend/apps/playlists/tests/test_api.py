import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.playlists.models import PlaylistType, PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory

pytestmark = pytest.mark.django_db


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_public_listing_only_contains_published_public_playlists():
    visible = PlaylistFactory(editorial=True)
    PlaylistItemFactory(playlist=visible, position=1)
    PlaylistFactory(visibility=PlaylistVisibility.UNLISTED)
    PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)
    PlaylistFactory(is_published=False)

    response = APIClient().get(reverse("playlists:list-create"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(visible.id)
    assert response.data["results"][0]["trackCount"] == 1
    assert "tracks" not in response.data["results"][0]


def test_owner_can_list_only_their_user_playlists_with_mine_filter():
    owner = UserFactory()
    private = PlaylistFactory(owner=owner, visibility=PlaylistVisibility.PRIVATE)
    unlisted = PlaylistFactory(owner=owner, visibility=PlaylistVisibility.UNLISTED)
    PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)

    response = authenticated_client(owner).get(
        reverse("playlists:list-create"),
        {"mine": "true"},
    )
    anonymous = APIClient().get(
        reverse("playlists:list-create"),
        {"mine": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert {item["id"] for item in response.data["results"]} == {
        str(private.id),
        str(unlisted.id),
    }
    assert all(item["isOwnedByCurrentUser"] for item in response.data["results"])
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED


def test_unlisted_is_available_by_direct_url_but_private_is_not():
    unlisted = PlaylistFactory(
        editorial=True,
        visibility=PlaylistVisibility.UNLISTED,
    )
    private = PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)

    unlisted_response = APIClient().get(
        reverse("playlists:detail", kwargs={"slug": unlisted.slug})
    )
    private_response = APIClient().get(
        reverse("playlists:detail", kwargs={"slug": private.slug})
    )

    assert unlisted_response.status_code == status.HTTP_200_OK
    assert private_response.status_code == status.HTTP_404_NOT_FOUND


def test_owner_can_view_private_and_draft_playlist():
    playlist = PlaylistFactory(
        visibility=PlaylistVisibility.PRIVATE,
        is_published=False,
    )

    response = authenticated_client(playlist.owner).get(
        reverse("playlists:detail", kwargs={"slug": playlist.slug})
    )

    assert response.status_code == status.HTTP_200_OK


def test_user_create_forces_owner_and_rejects_editorial_type():
    user = UserFactory()
    client = authenticated_client(user)

    created = client.post(
        reverse("playlists:list-create"),
        {"titleNe": "मेरो सूची", "visibility": "private"},
        format="json",
    )
    forbidden = client.post(
        reverse("playlists:list-create"),
        {"titleNe": "सम्पादकीय", "playlistType": "editorial"},
        format="json",
    )

    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["playlistType"] == "user"
    assert user.playlists.filter(id=created.data["id"]).exists()
    assert forbidden.status_code == status.HTTP_400_BAD_REQUEST


def test_user_cannot_create_or_change_a_playlist_to_public():
    user = UserFactory()
    playlist = PlaylistFactory(owner=user)
    client = authenticated_client(user)

    created = client.post(
        reverse("playlists:list-create"),
        {"titleNe": "सार्वजनिक सूची", "visibility": "public"},
        format="json",
    )
    changed = client.patch(
        reverse("playlists:visibility", kwargs={"slug": playlist.slug}),
        {"visibility": "public"},
        format="json",
    )

    assert created.status_code == status.HTTP_400_BAD_REQUEST
    assert changed.status_code == status.HTTP_400_BAD_REQUEST


def test_staff_can_create_editorial_playlist():
    staff = UserFactory(is_staff=True)

    response = authenticated_client(staff).post(
        reverse("playlists:list-create"),
        {
            "titleNe": "सम्पादकीय छनोट",
            "playlistType": "editorial",
            "visibility": "public",
            "isPublished": True,
            "isFeatured": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["playlistType"] == "editorial"
    assert response.data["isPublished"] is True
    assert response.data["isFeatured"] is True


def test_anonymous_user_cannot_create_playlist():
    response = APIClient().post(
        reverse("playlists:list-create"),
        {"titleNe": "मेरो सूची"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_cannot_modify_another_users_playlist():
    playlist = PlaylistFactory()

    response = authenticated_client(UserFactory()).patch(
        reverse("playlists:detail", kwargs={"slug": playlist.slug}),
        {"titleNe": "अनधिकृत"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_cannot_view_or_modify_another_users_private_playlist():
    playlist = PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)
    client = authenticated_client(UserFactory(is_staff=True))

    viewed = client.get(reverse("playlists:detail", kwargs={"slug": playlist.slug}))
    updated = client.patch(
        reverse("playlists:detail", kwargs={"slug": playlist.slug}),
        {"titleNe": "Staff edit"},
        format="json",
    )

    assert viewed.status_code == status.HTTP_404_NOT_FOUND
    assert updated.status_code == status.HTTP_404_NOT_FOUND


def test_owner_can_update_change_visibility_and_delete():
    playlist = PlaylistFactory(visibility=PlaylistVisibility.PRIVATE)
    client = authenticated_client(playlist.owner)

    updated = client.patch(
        reverse("playlists:detail", kwargs={"slug": playlist.slug}),
        {"titleNe": "नयाँ शीर्षक"},
        format="json",
    )
    visibility = client.patch(
        reverse("playlists:visibility", kwargs={"slug": playlist.slug}),
        {"visibility": "unlisted"},
        format="json",
    )
    deleted = client.delete(reverse("playlists:detail", kwargs={"slug": playlist.slug}))

    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["title"] == "नयाँ शीर्षक"
    assert visibility.data["visibility"] == "unlisted"
    assert deleted.status_code == status.HTTP_204_NO_CONTENT


def test_track_add_remove_and_reorder_preserve_stable_order():
    playlist = PlaylistFactory()
    tracks = AudioTrackFactory.create_batch(3)
    client = authenticated_client(playlist.owner)

    for track in tracks:
        response = client.post(
            reverse("playlists:add-track", kwargs={"slug": playlist.slug}),
            {"trackId": str(track.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    reordered = client.post(
        reverse("playlists:reorder", kwargs={"slug": playlist.slug}),
        {"trackIds": [str(tracks[2].id), str(tracks[0].id), str(tracks[1].id)]},
        format="json",
    )
    removed = client.post(
        reverse("playlists:remove-track", kwargs={"slug": playlist.slug}),
        {"trackId": str(tracks[0].id)},
        format="json",
    )

    assert [item["id"] for item in reordered.data["tracks"]] == [
        str(tracks[2].id),
        str(tracks[0].id),
        str(tracks[1].id),
    ]
    assert [item["id"] for item in removed.data["tracks"]] == [
        str(tracks[2].id),
        str(tracks[1].id),
    ]
    assert list(playlist.items.values_list("position", flat=True)) == [1, 2]


def test_track_without_a_stream_cannot_be_added():
    playlist = PlaylistFactory()
    track = AudioTrackFactory(stream_file_low="", stream_file_high="")

    response = authenticated_client(playlist.owner).post(
        reverse("playlists:add-track", kwargs={"slug": playlist.slug}),
        {"trackId": str(track.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "publicly playable" in str(response.data)


def test_reorder_requires_every_current_track_once():
    playlist = PlaylistFactory()
    item = PlaylistItemFactory(playlist=playlist, position=1)

    response = authenticated_client(playlist.owner).post(
        reverse("playlists:reorder", kwargs={"slug": playlist.slug}),
        {"trackIds": [str(item.track_id), str(item.track_id)]},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_duplicate_copies_order_into_private_user_playlist():
    source = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
    )
    first = PlaylistItemFactory(playlist=source, position=1, added_by=None)
    second = PlaylistItemFactory(playlist=source, position=2, added_by=None)
    user = UserFactory()

    response = authenticated_client(user).post(
        reverse("playlists:duplicate", kwargs={"slug": source.slug}),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["visibility"] == "private"
    assert response.data["playlistType"] == "user"
    assert [track["id"] for track in response.data["tracks"]] == [
        str(first.track_id),
        str(second.track_id),
    ]


def test_featured_endpoint_only_returns_published_public_editorial_playlists():
    featured = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_featured=True,
    )
    PlaylistFactory(is_featured=False)

    response = APIClient().get(reverse("playlists:featured"))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(featured.id)


def test_public_playlist_list_uses_compact_payload_and_bounded_queries():
    cache.clear()
    for _ in range(4):
        playlist = PlaylistFactory(editorial=True)
        PlaylistItemFactory.create_batch(2, playlist=playlist)

    with CaptureQueriesContext(connection) as queries:
        response = APIClient().get(reverse("playlists:list-create"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 4
    assert all("tracks" not in item for item in response.data["results"])
    assert all("description" not in item for item in response.data["results"])
    assert len(queries) <= 3


def test_public_playlist_detail_has_bounded_queries():
    cache.clear()
    playlist = PlaylistFactory(editorial=True)
    PlaylistItemFactory.create_batch(5, playlist=playlist)

    with CaptureQueriesContext(connection) as queries:
        response = APIClient().get(
            reverse("playlists:detail", kwargs={"slug": playlist.slug})
        )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["tracks"]) == 5
    assert len(queries) <= 4
