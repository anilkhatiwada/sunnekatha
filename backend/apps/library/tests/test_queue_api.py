import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import UserQueue, UserQueueItem

pytestmark = pytest.mark.django_db


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def replace_queue(client, tracks, current_index=0, position_seconds=0):
    return client.put(
        reverse("listening_progress:queue"),
        {
            "trackIds": [str(track.id) for track in tracks],
            "currentIndex": current_index,
            "positionSeconds": position_seconds,
        },
        format="json",
    )


def test_queue_requires_authentication():
    response = APIClient().get(reverse("listening_progress:queue"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_queue_is_scoped_to_owner():
    first_user = UserFactory()
    second_user = UserFactory()
    first_track = AudioTrackFactory()
    second_track = AudioTrackFactory()
    replace_queue(client_for(first_user), [first_track])
    replace_queue(client_for(second_user), [second_track])

    first = client_for(first_user).get(reverse("listening_progress:queue"))
    second = client_for(second_user).get(reverse("listening_progress:queue"))

    assert first.data["items"][0]["track"]["id"] == str(first_track.id)
    assert second.data["items"][0]["track"]["id"] == str(second_track.id)
    assert UserQueue.objects.count() == 2


def test_replace_queue_preserves_order_and_state():
    user = UserFactory()
    tracks = AudioTrackFactory.create_batch(3)

    response = replace_queue(
        client_for(user),
        tracks,
        current_index=1,
        position_seconds=42.5,
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["track"]["id"] for item in response.data["items"]] == [
        str(track.id) for track in tracks
    ]
    assert [item["position"] for item in response.data["items"]] == [1, 2, 3]
    assert response.data["currentIndex"] == 1
    assert response.data["positionSeconds"] == 42.5


def test_duplicate_tracks_are_distinct_stable_queue_items():
    user = UserFactory()
    track = AudioTrackFactory()

    response = replace_queue(client_for(user), [track, track])

    items = response.data["items"]
    assert len(items) == 2
    assert items[0]["track"]["id"] == items[1]["track"]["id"]
    assert items[0]["id"] != items[1]["id"]


def test_add_track_and_play_next_keep_stable_order():
    user = UserFactory()
    tracks = AudioTrackFactory.create_batch(3)
    client = client_for(user)
    replace_queue(client, tracks[:2], current_index=0)

    added = client.post(
        reverse("listening_progress:queue-add"),
        {"trackId": str(tracks[2].id)},
        format="json",
    )
    next_track = AudioTrackFactory()
    prioritized = client.post(
        reverse("listening_progress:queue-play-next"),
        {"trackId": str(next_track.id)},
        format="json",
    )

    assert [item["track"]["id"] for item in added.data["items"]] == [
        str(track.id) for track in tracks
    ]
    assert [item["track"]["id"] for item in prioritized.data["items"]] == [
        str(tracks[0].id),
        str(next_track.id),
        str(tracks[1].id),
        str(tracks[2].id),
    ]


def test_reorder_uses_item_ids_and_preserves_current_item():
    user = UserFactory()
    client = client_for(user)
    initial = replace_queue(
        client,
        AudioTrackFactory.create_batch(3),
        current_index=1,
        position_seconds=25,
    )
    items = initial.data["items"]

    response = client.patch(
        reverse("listening_progress:queue-reorder"),
        {"itemIds": [items[2]["id"], items[1]["id"], items[0]["id"]]},
        format="json",
    )

    assert [item["id"] for item in response.data["items"]] == [
        items[2]["id"],
        items[1]["id"],
        items[0]["id"],
    ]
    assert response.data["currentIndex"] == 1
    assert response.data["positionSeconds"] == 25.0


def test_reorder_requires_every_item_once():
    user = UserFactory()
    client = client_for(user)
    initial = replace_queue(client, AudioTrackFactory.create_batch(2))
    item_id = initial.data["items"][0]["id"]

    response = client.patch(
        reverse("listening_progress:queue-reorder"),
        {"itemIds": [item_id, item_id]},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_item_compacts_order_and_protects_other_users_items():
    owner = UserFactory()
    client = client_for(owner)
    initial = replace_queue(client, AudioTrackFactory.create_batch(3), current_index=1)
    removed_id = initial.data["items"][0]["id"]
    another = replace_queue(
        client_for(UserFactory()),
        [AudioTrackFactory()],
    ).data["items"][0]["id"]

    removed = client.delete(
        reverse(
            "listening_progress:queue-remove",
            kwargs={"item_id": removed_id},
        )
    )
    forbidden = client.delete(
        reverse(
            "listening_progress:queue-remove",
            kwargs={"item_id": another},
        )
    )
    current = client.get(reverse("listening_progress:queue"))

    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert forbidden.status_code == status.HTTP_400_BAD_REQUEST
    assert [item["position"] for item in current.data["items"]] == [1, 2]
    assert current.data["currentIndex"] == 0


def test_clear_queue_is_idempotent():
    user = UserFactory()
    client = client_for(user)
    replace_queue(client, AudioTrackFactory.create_batch(2))

    first = client.delete(reverse("listening_progress:queue"))
    second = client.delete(reverse("listening_progress:queue"))
    current = client.get(reverse("listening_progress:queue"))

    assert first.status_code == status.HTTP_204_NO_CONTENT
    assert second.status_code == status.HTTP_204_NO_CONTENT
    assert current.data["items"] == []
    assert current.data["currentIndex"] == -1
    assert current.data["positionSeconds"] == 0.0


def test_queue_position_shuffle_and_repeat_updates():
    user = UserFactory()
    client = client_for(user)
    replace_queue(client, AudioTrackFactory.create_batch(2))

    position = client.patch(
        reverse("listening_progress:queue-position"),
        {"currentIndex": 1, "positionSeconds": 64},
        format="json",
    )
    shuffle = client.patch(
        reverse("listening_progress:queue-shuffle"),
        {"isShuffleEnabled": True},
        format="json",
    )
    repeat = client.patch(
        reverse("listening_progress:queue-repeat"),
        {"repeatMode": "all"},
        format="json",
    )

    assert position.data["currentIndex"] == 1
    assert position.data["positionSeconds"] == 64.0
    assert shuffle.data["isShuffleEnabled"] is True
    assert repeat.data["repeatMode"] == "all"


def test_queue_get_has_bounded_queries(django_assert_num_queries):
    user = UserFactory()
    client = client_for(user)
    replace_queue(client, AudioTrackFactory.create_batch(3))

    with django_assert_num_queries(5):
        response = client.get(reverse("listening_progress:queue"))

    assert len(response.data["items"]) == 3


def test_queue_positions_are_database_unique():
    queue = UserQueue.objects.create(user=UserFactory())
    UserQueueItem.objects.create(
        queue=queue,
        track=AudioTrackFactory(),
        position=1,
    )

    with pytest.raises(IntegrityError):
        UserQueueItem.objects.create(
            queue=queue,
            track=AudioTrackFactory(),
            position=1,
        )
