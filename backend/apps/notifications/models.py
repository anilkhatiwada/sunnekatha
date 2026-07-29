from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class NotificationType(models.TextChoices):
    FOLLOWED_AUTHOR_PUBLISHED = (
        "followed_author_published",
        "Followed author published new content",
    )
    FOLLOWED_NARRATOR_PUBLISHED = (
        "followed_narrator_published",
        "Followed narrator published new content",
    )
    PLAYLIST_UPDATED = "playlist_updated", "Playlist updated"
    UPLOAD_PROCESSING_COMPLETED = (
        "upload_processing_completed",
        "Upload processing completed",
    )
    UPLOAD_PROCESSING_FAILED = (
        "upload_processing_failed",
        "Upload processing failed",
    )
    CREATOR_SUBMISSION_APPROVED = (
        "creator_submission_approved",
        "Creator submission approved",
    )
    CREATOR_SUBMISSION_REJECTED = (
        "creator_submission_rejected",
        "Creator submission rejected",
    )
    CREATOR_CHANGES_REQUESTED = (
        "creator_changes_requested",
        "Creator submission changes requested",
    )


class Notification(UUIDTimeStampedModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="notifications",
        on_delete=models.CASCADE,
    )
    notification_type = models.CharField(
        max_length=48,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    read_at = models.DateTimeField(blank=True, null=True, db_index=True)
    deduplication_key = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("recipient", "deduplication_key"),
                condition=~models.Q(deduplication_key=""),
                name="notification_unique_recipient_dedup",
            )
        ]
        indexes = [
            models.Index(
                fields=("recipient", "read_at", "-created_at"),
                name="notif_recipient_unread_idx",
            )
        ]

    def __str__(self):
        return f"{self.recipient}: {self.title}"
