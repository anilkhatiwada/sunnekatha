from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.common.storage import processed_audio_storage
from apps.common.uploads import processed_audio_upload_path
from apps.common.validators import validate_audio_upload


class AudioAdvertisement(UUIDTimeStampedModel):
    title = models.CharField(max_length=180)
    audio_file = models.FileField(
        upload_to=processed_audio_upload_path,
        storage=processed_audio_storage,
        validators=[validate_audio_upload],
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    frequency = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(2)],
        help_text="Minimum main-audio starts between plays of this advertisement.",
    )
    is_enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-is_enabled", "title", "id")

    def __str__(self):
        return self.title


class AudioAdvertisementPlayback(UUIDTimeStampedModel):
    advertisement = models.ForeignKey(
        AudioAdvertisement,
        related_name="playbacks",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audio_ad_playbacks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    track = models.ForeignKey(
        "catalog.AudioTrack",
        related_name="audio_ad_playbacks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    session_id = models.UUIDField(db_index=True)
    playback_sequence = models.PositiveBigIntegerField()
    source = models.CharField(max_length=24)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-started_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("advertisement", "session_id", "playback_sequence"),
                name="audio_ads_unique_started_playback",
            )
        ]
        indexes = [
            models.Index(
                fields=("advertisement", "-started_at"),
                name="audio_ads_ad_started_idx",
            ),
            models.Index(
                fields=("session_id", "-playback_sequence"),
                name="audio_ads_session_seq_idx",
            ),
        ]

    def __str__(self):
        return f"{self.advertisement} at {self.started_at}"
