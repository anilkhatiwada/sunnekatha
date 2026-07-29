from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import ListeningProgress

pytestmark = pytest.mark.django_db


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def progress_url(track):
    return reverse(
        "listening_progress:detail",
        kwargs={"track_id": track.id},
    )


def update_progress(client, track, position, duration=None):
    return client.put(
        progress_url(track),
        {
            "progressSeconds": position,
            "durationSeconds": duration or track.duration_seconds,
        },
        format="json",
    )


def test_progress_update_and_resume_position():
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=600)
    client = client_for(user)

    updated = update_progress(client, track, 123.5)
    resumed = client.get(progress_url(track))

    assert updated.status_code == status.HTTP_200_OK
    assert resumed.status_code == status.HTTP_200_OK
    assert resumed.data["trackId"] == str(track.id)
    assert resumed.data["progressSeconds"] == 123.5
    assert resumed.data["durationSeconds"] == 600.0
    assert resumed.data["isCompleted"] is False


@pytest.mark.parametrize(
    ("position", "is_completed"),
    [(899, False), (900, True), (950, True)],
)
def test_completion_threshold_is_ninety_percent(position, is_completed):
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=1000)

    response = update_progress(client_for(user), track, position)

    assert response.data["isCompleted"] is is_completed


@pytest.mark.parametrize(
    ("position", "expected_status"),
    [(-1, status.HTTP_400_BAD_REQUEST), (106, status.HTTP_400_BAD_REQUEST)],
)
def test_invalid_positions_are_rejected(position, expected_status):
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=100)

    response = update_progress(client_for(user), track, position)

    assert response.status_code == expected_status
    assert not ListeningProgress.objects.filter(user=user, track=track).exists()


def test_small_duration_overshoot_is_clamped():
    track = AudioTrackFactory(duration_seconds=100)

    response = update_progress(client_for(UserFactory()), track, 105)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["progressSeconds"] == 100.0
    assert response.data["progressPercentage"] == 100.0
    assert response.data["isCompleted"] is True


def test_repeated_updates_reuse_one_database_row():
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=500)
    client = client_for(user)

    update_progress(client, track, 15)
    update_progress(client, track, 30)
    update_progress(client, track, 30)

    records = ListeningProgress.objects.filter(user=user, track=track)
    assert records.count() == 1
    assert float(records.get().position_seconds) == 30


def test_continue_listening_excludes_completed_short_track_and_orders_recently_used():
    user = UserFactory()
    client = client_for(user)
    older = AudioTrackFactory(duration_seconds=100)
    newer = AudioTrackFactory(duration_seconds=200)
    completed_short = AudioTrackFactory(duration_seconds=10)

    update_progress(client, older, 20)
    update_progress(client, newer, 30)
    update_progress(client, completed_short, 9)
    ListeningProgress.objects.filter(user=user, track=older).update(
        last_listened_at=timezone.now() - timedelta(hours=1)
    )

    response = client.get(reverse("listening_progress:continue-listening"))

    assert response.status_code == status.HTTP_200_OK
    assert [item["track"]["id"] for item in response.data["results"]] == [
        str(newer.id),
        str(older.id),
    ]
    assert response.data["results"][0]["progress"]["progressSeconds"] == 30.0


def test_mark_completed_and_remove_from_continue_listening_are_idempotent():
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=120)
    client = client_for(user)
    update_progress(client, track, 30)

    completed = client.post(
        reverse(
            "listening_progress:complete",
            kwargs={"track_id": track.id},
        )
    )
    removed = client.delete(
        reverse(
            "listening_progress:remove",
            kwargs={"track_id": track.id},
        )
    )
    removed_again = client.delete(progress_url(track))

    assert completed.data["isCompleted"] is True
    assert completed.data["progressSeconds"] == 120.0
    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert removed_again.status_code == status.HTTP_204_NO_CONTENT
    assert not ListeningProgress.objects.filter(user=user, track=track).exists()


def test_progress_is_scoped_to_authenticated_user():
    track = AudioTrackFactory()
    owner = UserFactory()
    update_progress(client_for(owner), track, 20)

    anonymous = APIClient().get(progress_url(track))
    another_user = client_for(UserFactory()).get(progress_url(track))

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert another_user.status_code == status.HTTP_404_NOT_FOUND


def test_continue_listening_has_bounded_queries(django_assert_num_queries):
    user = UserFactory()
    client = client_for(user)
    for position in (10, 20, 30):
        update_progress(client, AudioTrackFactory(duration_seconds=100), position)

    with django_assert_num_queries(4):
        response = client.get(reverse("listening_progress:continue-listening"))

    assert response.data["count"] == 3


def test_progress_update_has_bounded_queries():
    user = UserFactory()
    track = AudioTrackFactory(duration_seconds=100)

    with CaptureQueriesContext(connection) as queries:
        response = update_progress(client_for(user), track, 25)

    assert response.status_code == status.HTTP_200_OK
    assert len(queries) <= 9
