import factory
from factory.django import DjangoModelFactory

from apps.audio_ads.models import AudioAdvertisement


class AudioAdvertisementFactory(DjangoModelFactory):
    class Meta:
        model = AudioAdvertisement

    title = factory.Sequence(lambda number: f"Audio advertisement {number}")
    audio_file = "processed/audio/audioadvertisement/test.mp3"
    duration_seconds = 12
    frequency = 3
    is_enabled = True
