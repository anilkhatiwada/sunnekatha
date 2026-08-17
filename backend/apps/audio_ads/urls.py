from django.urls import path

from apps.audio_ads.views import (
    AudioAdvertisementStartedView,
    NextAudioAdvertisementView,
)

app_name = "audio_ads"

urlpatterns = [
    path("next/", NextAudioAdvertisementView.as_view(), name="next"),
    path(
        "<uuid:advertisement_id>/started/",
        AudioAdvertisementStartedView.as_view(),
        name="started",
    ),
]
