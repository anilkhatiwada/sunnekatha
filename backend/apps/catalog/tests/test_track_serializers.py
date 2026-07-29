from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db

PRIVATE_FIELDS = {
    "audio_master_file",
    "stream_file_high",
    "stream_file_low",
    "audioMasterFile",
    "streamFileHigh",
    "streamFileLow",
}


def test_compact_and_detailed_serializers_never_expose_storage_fields():
    track = AudioTrackFactory(
        audio_master_file="private/master.wav",
        stream_file_high="private/high.mp3",
        stream_file_low="private/low.mp3",
    )

    compact = APIClient().get(reverse("catalog:track-list")).data["results"][0]
    detailed = (
        APIClient()
        .get(reverse("catalog:track-detail", kwargs={"slug": track.slug}))
        .data
    )

    assert PRIVATE_FIELDS.isdisjoint(compact)
    assert PRIVATE_FIELDS.isdisjoint(detailed)
    assert "private/master.wav" not in str(compact)
    assert "private/master.wav" not in str(detailed)
    assert "waveform" not in compact
    assert "waveform" in detailed


def test_track_payload_matches_frontend_subtitle_and_work_summary():
    track = AudioTrackFactory(
        work__content_type="novel_chapter",
        work__subtitle_ne="पहिलो भाग",
        chapter_number=2,
    )

    compact = APIClient().get(reverse("catalog:track-list")).data["results"][0]
    detailed = (
        APIClient()
        .get(reverse("catalog:track-detail", kwargs={"slug": track.slug}))
        .data
    )

    assert compact["subtitle"] == "पहिलो भाग"
    assert detailed["literaryWork"]["type"] == "novel"
    assert detailed["literaryWork"]["contentType"] == "novel_chapter"


def test_player_serializer_gets_media_only_from_service():
    track = AudioTrackFactory(
        stream_file_high="private/high.mp3",
        stream_file_low="private/low.mp3",
    )
    access_urls = {
        "high": "https://media.example.com/signed-high",
        "low": "https://media.example.com/signed-low",
    }

    with patch(
        "apps.catalog.track_serializers.track_media_url_service.get_access_urls",
        return_value=access_urls,
    ) as media_service:
        response = APIClient().get(
            reverse("catalog:track-player", kwargs={"slug": track.slug})
        )

    assert response.data["media"] == access_urls
    assert PRIVATE_FIELDS.isdisjoint(response.data)
    media_service.assert_called_once()


def test_premium_player_hides_urls_without_entitlement():
    track = AudioTrackFactory(
        is_premium=True,
        stream_file_high="private/high.mp3",
        stream_file_low="private/low.mp3",
    )

    response = APIClient().get(
        reverse("catalog:track-player", kwargs={"slug": track.slug})
    )

    assert response.data["media"] == {"high": None, "low": None}
