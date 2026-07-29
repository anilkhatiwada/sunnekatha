from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import (
    ListeningHistory,
    ListeningProgress,
    PlaybackEvent,
    PlaybackEventType,
    PlaybackSession,
)

pytestmark = pytest.mark.django_db


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def start_session(client, track, device_id="web-browser"):
    return client.post(
        reverse("listening_progress:session-start"),
        {
            "trackId": str(track.id),
            "deviceId": device_id,
            "positionSeconds": 0,
        },
        format="json",
    )


def update_session(client, session_id, **payload):
    return client.patch(
        reverse(
            "listening_progress:session-update",
            kwargs={"session_id": session_id},
        ),
        payload,
        format="json",
    )


def end_session(client, session_id, **payload):
    return client.post(
        reverse(
            "listening_progress:session-end",
            kwargs={"session_id": session_id},
        ),
        payload,
        format="json",
    )


def test_start_session_creates_sparse_started_event():
    user = UserFactory()
    track = AudioTrackFactory()

    response = start_session(client_for(user), track)

    assert response.status_code == status.HTTP_201_CREATED
    session = PlaybackSession.objects.get(pk=response.data["id"])
    assert session.user == user
    assert session.track == track
    assert list(session.events.values_list("event_type", flat=True)) == ["started"]
    history = ListeningHistory.objects.get(user=user, track=track)
    assert history.play_count == 1
    assert history.total_listened_seconds == 0
    assert not ListeningProgress.objects.filter(user=user, track=track).exists()


def test_repeated_start_reuses_active_session_without_duplicate_event():
    user = UserFactory()
    track = AudioTrackFactory()
    client = client_for(user)

    first = start_session(client, track)
    second = start_session(client, track)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_200_OK
    assert first.data["id"] == second.data["id"]
    assert PlaybackSession.objects.count() == 1
    assert PlaybackEvent.objects.count() == 1
    assert ListeningHistory.objects.get(user=user, track=track).play_count == 1


def test_different_device_creates_a_separate_active_session():
    user = UserFactory()
    track = AudioTrackFactory()
    client = client_for(user)

    start_session(client, track, "phone")
    start_session(client, track, "browser")

    assert PlaybackSession.objects.filter(user=user, track=track).count() == 2


def test_session_update_is_cumulative_and_deduplicates_transition_events():
    user = UserFactory()
    track = AudioTrackFactory()
    client = client_for(user)
    session_id = start_session(client, track).data["id"]

    first = update_session(
        client,
        session_id,
        listenedSeconds=30,
        eventType="paused",
        positionSeconds=40,
    )
    repeated = update_session(
        client,
        session_id,
        listenedSeconds=30,
        eventType="paused",
        positionSeconds=40,
    )
    lower_retry = update_session(client, session_id, listenedSeconds=20)

    assert first.status_code == status.HTTP_200_OK
    assert repeated.status_code == status.HTTP_200_OK
    assert lower_retry.data["listenedSeconds"] == 30.0
    assert (
        PlaybackEvent.objects.filter(
            session_id=session_id,
            event_type=PlaybackEventType.PAUSED,
        ).count()
        == 1
    )


def test_client_event_id_prevents_duplicate_raw_events():
    user = UserFactory()
    client = client_for(user)
    session_id = start_session(client, AudioTrackFactory()).data["id"]
    payload = {
        "listenedSeconds": 10,
        "eventType": "seeked",
        "positionSeconds": 70,
        "clientEventId": "seek-123",
    }

    update_session(client, session_id, **payload)
    update_session(client, session_id, **payload)

    assert (
        PlaybackEvent.objects.filter(
            session_id=session_id,
            deduplication_key="seek-123",
        ).count()
        == 1
    )


def test_end_session_is_idempotent_and_rolls_history_up_once():
    user = UserFactory()
    track = AudioTrackFactory()
    client = client_for(user)
    session_id = start_session(client, track).data["id"]

    first = end_session(
        client,
        session_id,
        listenedSeconds=90,
        completed=True,
        positionSeconds=track.duration_seconds,
    )
    repeated = end_session(
        client,
        session_id,
        listenedSeconds=90,
        completed=True,
    )

    history = ListeningHistory.objects.get(user=user, track=track)
    assert first.status_code == status.HTTP_200_OK
    assert repeated.status_code == status.HTTP_200_OK
    assert history.total_listened_seconds == 90
    assert history.play_count == 1
    assert history.completion_count == 1
    assert PlaybackEvent.objects.filter(session_id=session_id).count() == 2


def test_multiple_ended_sessions_accumulate_one_history_rollup():
    user = UserFactory()
    track = AudioTrackFactory()
    client = client_for(user)

    first = start_session(client, track, "phone").data["id"]
    end_session(client, first, listenedSeconds=25)
    second = start_session(client, track, "browser").data["id"]
    end_session(client, second, listenedSeconds=35, completed=True)

    history = ListeningHistory.objects.get(user=user, track=track)
    assert history.total_listened_seconds == 60
    assert history.play_count == 2
    assert history.completion_count == 1


def test_negative_listened_seconds_are_rejected():
    user = UserFactory()
    client = client_for(user)
    session_id = start_session(client, AudioTrackFactory()).data["id"]

    response = update_session(client, session_id, listenedSeconds=-1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_user_cannot_update_another_users_session():
    owner = UserFactory()
    session_id = start_session(client_for(owner), AudioTrackFactory()).data["id"]

    response = update_session(
        client_for(UserFactory()),
        session_id,
        listenedSeconds=10,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_recently_played_and_history_are_user_scoped_and_ordered():
    user = UserFactory()
    older_track = AudioTrackFactory()
    newer_track = AudioTrackFactory()
    other_track = AudioTrackFactory()
    older = ListeningHistory.objects.create(
        user=user,
        track=older_track,
        first_listened_at=timezone.now() - timedelta(days=2),
        last_listened_at=timezone.now() - timedelta(hours=2),
        total_listened_seconds=20,
        play_count=1,
    )
    ListeningHistory.objects.create(
        user=user,
        track=newer_track,
        first_listened_at=timezone.now() - timedelta(days=1),
        last_listened_at=timezone.now() - timedelta(hours=1),
        total_listened_seconds=40,
        play_count=2,
    )
    ListeningHistory.objects.create(
        user=UserFactory(),
        track=other_track,
        first_listened_at=timezone.now(),
        last_listened_at=timezone.now(),
        total_listened_seconds=10,
        play_count=1,
    )
    client = client_for(user)

    recent = client.get(reverse("listening_progress:recently-played"))
    history = client.get(reverse("listening_progress:history"))

    expected = [str(newer_track.id), str(older.track_id)]
    assert [item["track"]["id"] for item in recent.data["results"]] == expected
    assert [item["track"]["id"] for item in history.data["results"]] == expected
    assert history.data["results"][0]["playCount"] == 2


def test_history_list_has_bounded_queries(django_assert_num_queries):
    user = UserFactory()
    for seconds in (10, 20, 30):
        track = AudioTrackFactory()
        ListeningHistory.objects.create(
            user=user,
            track=track,
            first_listened_at=timezone.now(),
            last_listened_at=timezone.now(),
            total_listened_seconds=seconds,
            play_count=1,
        )

    with django_assert_num_queries(4):
        response = client_for(user).get(reverse("listening_progress:history"))

    assert response.data["count"] == 3
