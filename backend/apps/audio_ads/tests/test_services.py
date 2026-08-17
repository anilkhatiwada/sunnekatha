import uuid

import pytest

from apps.audio_ads.services import audio_advertisement_service
from apps.audio_ads.tests.factories import AudioAdvertisementFactory

pytestmark = pytest.mark.django_db


def test_ad_is_not_eligible_before_its_frequency():
    AudioAdvertisementFactory(frequency=3)

    selection = audio_advertisement_service.select_for_playback(
        session_id=uuid.uuid4(),
        playback_sequence=2,
    )

    assert selection.advertisement is None
    assert selection.reason == "frequency_not_reached"


def test_started_playback_controls_frequency_and_is_idempotent():
    advertisement = AudioAdvertisementFactory(frequency=2)
    session_id = uuid.uuid4()
    selection = audio_advertisement_service.select_for_playback(
        session_id=session_id,
        playback_sequence=2,
    )
    assert selection.advertisement == advertisement

    first, created = audio_advertisement_service.record_started(
        advertisement=advertisement,
        session_id=session_id,
        playback_sequence=2,
        source="playlist",
        track=None,
        user=None,
    )
    duplicate, duplicate_created = audio_advertisement_service.record_started(
        advertisement=advertisement,
        session_id=session_id,
        playback_sequence=2,
        source="playlist",
        track=None,
        user=None,
    )
    assert created is True
    assert duplicate_created is False
    assert duplicate.pk == first.pk

    too_soon = audio_advertisement_service.select_for_playback(
        session_id=session_id,
        playback_sequence=3,
    )
    assert too_soon.advertisement is None

    due = audio_advertisement_service.select_for_playback(
        session_id=session_id,
        playback_sequence=4,
    )
    assert due.advertisement == advertisement


def test_disabled_ad_is_never_selected():
    AudioAdvertisementFactory(frequency=2, is_enabled=False)

    selection = audio_advertisement_service.select_for_playback(
        session_id=uuid.uuid4(),
        playback_sequence=10,
    )

    assert selection.advertisement is None
    assert selection.reason == "no_enabled_ads"


def test_selection_rotates_to_an_ad_that_has_not_played_in_the_session():
    first = AudioAdvertisementFactory(frequency=2)
    second = AudioAdvertisementFactory(frequency=2)
    session_id = uuid.uuid4()
    selected = audio_advertisement_service.select_for_playback(
        session_id=session_id,
        playback_sequence=2,
    ).advertisement
    assert selected in {first, second}
    audio_advertisement_service.record_started(
        advertisement=selected,
        session_id=session_id,
        playback_sequence=2,
        source="playlist",
        track=None,
        user=None,
    )

    next_selection = audio_advertisement_service.select_for_playback(
        session_id=session_id,
        playback_sequence=4,
    )

    assert next_selection.advertisement in {first, second} - {selected}
