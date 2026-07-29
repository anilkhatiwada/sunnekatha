import pytest

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.playback import playback_session_service

pytestmark = pytest.mark.django_db


def test_new_session_increments_cached_play_count_once():
    user = UserFactory()
    track = AudioTrackFactory(play_count_cache=0)

    playback_session_service.start(user=user, track=track, device_id="browser")
    playback_session_service.start(user=user, track=track, device_id="browser")

    track.refresh_from_db()
    assert track.play_count_cache == 1
