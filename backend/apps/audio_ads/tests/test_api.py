import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.audio_ads.models import AudioAdvertisementPlayback
from apps.audio_ads.tests.factories import AudioAdvertisementFactory
from apps.catalog.tests.factories import AudioTrackFactory

pytestmark = pytest.mark.django_db


@patch("apps.audio_ads.views.cloudfront_media_service.deliver_audio_advertisement")
def test_next_ad_returns_eligible_media_delivery(deliver):
    advertisement = AudioAdvertisementFactory(frequency=2)
    deliver.return_value = {
        "id": advertisement.pk,
        "title": advertisement.title,
        "url": "https://media.example.com/restricted/ad.mp3?Policy=signed",
        "duration": 12,
        "expiresAt": None,
    }

    response = APIClient().post(
        reverse("audio_ads:next"),
        {
            "sessionId": str(uuid.uuid4()),
            "playbackSequence": 2,
            "source": "playlist",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["advertisement"]["id"] == str(advertisement.pk)


def test_started_endpoint_counts_only_once():
    advertisement = AudioAdvertisementFactory(frequency=2)
    track = AudioTrackFactory()
    session_id = uuid.uuid4()
    payload = {
        "sessionId": str(session_id),
        "playbackSequence": 2,
        "trackId": str(track.pk),
        "source": "playlist",
    }
    client = APIClient()

    first = client.post(
        reverse("audio_ads:started", args=[advertisement.pk]),
        payload,
        format="json",
    )
    second = client.post(
        reverse("audio_ads:started", args=[advertisement.pk]),
        payload,
        format="json",
    )

    assert first.status_code == 200
    assert first.data == {"counted": True}
    assert second.data == {"counted": False}
    assert AudioAdvertisementPlayback.objects.count() == 1
