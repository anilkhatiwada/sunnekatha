import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.audio_ads.models import AudioAdvertisement, AudioAdvertisementPlayback
from apps.audio_ads.services import audio_advertisement_service
from apps.audio_ads.tests.factories import AudioAdvertisementFactory
from apps.catalog.audio_processing import AudioProcessingError

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


def test_ad_admin_does_not_require_duration(client, mocker):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)
    detect = mocker.patch(
        "apps.audio_ads.admin.audio_advertisement_metadata_service.detect_duration",
        return_value=17,
    )

    response = client.post(
        reverse("admin:audio_ads_audioadvertisement_add"),
        {
            "title": "Station announcement",
            "audio_file": SimpleUploadedFile(
                "announcement.mp3", b"ID3" + (b"0" * 128), content_type="audio/mpeg"
            ),
            "frequency": 3,
            "is_enabled": "on",
        },
    )

    assert response.status_code == 302
    advertisement = AudioAdvertisement.objects.get(title="Station announcement")
    assert advertisement.duration_seconds == 17
    detect.assert_called_once_with(advertisement)


def test_ad_admin_disables_ad_when_duration_detection_fails(client, mocker):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)
    mocker.patch(
        "apps.audio_ads.admin.audio_advertisement_metadata_service.detect_duration",
        side_effect=AudioProcessingError("metadata", "Duration unavailable."),
    )

    response = client.post(
        reverse("admin:audio_ads_audioadvertisement_add"),
        {
            "title": "Broken announcement",
            "audio_file": SimpleUploadedFile(
                "announcement.mp3", b"ID3" + (b"0" * 128), content_type="audio/mpeg"
            ),
            "frequency": 3,
            "is_enabled": "on",
        },
        follow=True,
    )

    assert response.status_code == 200
    advertisement = AudioAdvertisement.objects.get(title="Broken announcement")
    assert advertisement.duration_seconds == 0
    assert advertisement.is_enabled is False
    assert "The ad was disabled" in response.content.decode()
