import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.audio_ads.models import AudioAdvertisementPlayback
from apps.audio_ads.services import audio_advertisement_service
from apps.audio_ads.tests.factories import AudioAdvertisementFactory

pytestmark = pytest.mark.django_db


def test_superuser_can_manage_ads_and_view_analytics(client):
    staff = UserFactory(is_staff=True, is_superuser=True)
    advertisement = AudioAdvertisementFactory(frequency=5)
    audio_advertisement_service.record_started(
        advertisement=advertisement,
        session_id="8ebc26b4-2f30-4dc0-a7f4-6c12d3523951",
        playback_sequence=5,
        source="playlist",
        track=None,
        user=staff,
    )
    client.force_login(staff)

    response = client.get(reverse("admin:audio_ads_audioadvertisement_changelist"))
    change = client.get(
        reverse("admin:audio_ads_audioadvertisement_change", args=[advertisement.pk])
    )

    assert response.status_code == 200
    assert advertisement.title in response.content.decode()
    assert "Every 5 audios" in response.content.decode()
    assert "View playback history" in change.content.decode()
    assert AudioAdvertisementPlayback.objects.count() == 1


def test_nonstaff_cannot_access_audio_ad_admin(client):
    user = UserFactory()
    client.force_login(user)

    response = client.get(reverse("admin:audio_ads_audioadvertisement_changelist"))

    assert response.status_code == 302
