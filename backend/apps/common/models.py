"""Reusable abstract persistence models."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDTimeStampedModel(models.Model):
    """Abstract base for domain records with opaque UUID identity and timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class AdministrativeAuditAction(models.TextChoices):
    CREATED = "created", "Content created"
    EDITED = "edited", "Content edited"
    REVIEW_SUBMITTED = "review_submitted", "Review submitted"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    PUBLISHED = "published", "Published"
    UNPUBLISHED = "unpublished", "Unpublished"
    PROCESSING_RETRIED = "processing_retried", "Audio processing retried"
    PLAYLIST_REORDERED = "playlist_reordered", "Playlist reordered"
    HOMEPAGE_CHANGED = "homepage_changed", "Homepage changed"
    COPYRIGHT_VERIFIED = "copyright_verified", "Copyright verified"
    COPYRIGHT_REVOKED = "copyright_revoked", "Copyright verification revoked"
    SUBSCRIPTION_CHANGED = "subscription_changed", "Subscription changed"
    USER_SUSPENDED = "user_suspended", "User suspended"
    USER_REACTIVATED = "user_reactivated", "User reactivated"
    METADATA_IMPORTED = "metadata_imported", "Metadata imported"
    METADATA_EXPORTED = "metadata_exported", "Metadata exported"


class AdministrativeAudit(UUIDTimeStampedModel):
    staff_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="administrative_audits",
        on_delete=models.PROTECT,
    )
    action = models.CharField(
        max_length=32,
        choices=AdministrativeAuditAction.choices,
        db_index=True,
    )
    object_type = models.CharField(max_length=120, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=250)
    reason = models.TextField(blank=True)
    before_summary = models.JSONField(default=dict, blank=True)
    after_summary = models.JSONField(default=dict, blank=True)
    request_identifier = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")
        permissions = [
            ("import_metadata", "Can import controlled metadata"),
            ("export_metadata", "Can export controlled metadata"),
        ]
        indexes = [
            models.Index(
                fields=("object_type", "object_id", "-created_at"),
                name="admin_audit_object_idx",
            ),
            models.Index(
                fields=("staff_user", "-created_at"),
                name="admin_audit_staff_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.object_repr}"


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class PublicationQuerySet(models.QuerySet):
    """Visibility helpers for models with soft publication state."""

    def published(self):
        return self.filter(
            publication_status=PublicationStatus.PUBLISHED,
            published_at__lte=timezone.now(),
        )

    def drafts(self):
        return self.filter(publication_status=PublicationStatus.DRAFT)


class SoftPublishableModel(models.Model):
    """Abstract publication lifecycle without deleting unpublished records."""

    publication_status = models.CharField(
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(blank=True, null=True, db_index=True)

    objects = PublicationQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_published(self) -> bool:
        return (
            self.publication_status == PublicationStatus.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )

    def publish(self, *, at=None) -> None:
        self.publication_status = PublicationStatus.PUBLISHED
        self.published_at = at or timezone.now()

    def unpublish(self) -> None:
        self.publication_status = PublicationStatus.DRAFT
        self.published_at = None

    def archive(self) -> None:
        self.publication_status = PublicationStatus.ARCHIVED
