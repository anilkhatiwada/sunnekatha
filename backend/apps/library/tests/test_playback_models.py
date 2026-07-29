import pytest
from django.db import IntegrityError

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import PlaybackEvent, PlaybackSession

pytestmark = pytest.mark.django_db


def test_only_one_active_session_per_user_track_and_device():
    user = UserFactory()
    track = AudioTrackFactory()
    PlaybackSession.objects.create(user=user, track=track, device_id="browser")

    with pytest.raises(IntegrityError):
        PlaybackSession.objects.create(user=user, track=track, device_id="browser")


def test_event_deduplication_key_is_unique_within_session():
    session = PlaybackSession.objects.create(
        user=UserFactory(),
        track=AudioTrackFactory(),
        device_id="browser",
    )
    PlaybackEvent.objects.create(
        session=session,
        event_type="paused",
        deduplication_key="event-1",
    )

    with pytest.raises(IntegrityError):
        PlaybackEvent.objects.create(
            session=session,
            event_type="paused",
            deduplication_key="event-1",
        )
