from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class UploadType(models.TextChoices):
    AUDIO_MASTER = "audio_master", "Audio master"
    COVER_IMAGE = "cover_image", "Cover image"
    NARRATOR_IMAGE = "narrator_image", "Narrator image"
    AUTHOR_IMAGE = "author_image", "Author image"


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELED = "canceled", "Canceled"
    EXPIRED = "expired", "Expired"
    ABANDONED = "abandoned", "Abandoned"


class UploadSession(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="upload_sessions",
        on_delete=models.CASCADE,
    )
    upload_type = models.CharField(max_length=24, choices=UploadType.choices)
    object_key = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    expected_size = models.PositiveBigIntegerField()
    actual_size = models.PositiveBigIntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField(db_index=True)
    temporary_object_deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(
                fields=("user", "status", "-created_at"),
                name="upload_user_status_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expected_size__gt=0),
                name="upload_expected_size_positive",
            )
        ]

    def __str__(self):
        return f"{self.upload_type}: {self.original_filename}"
