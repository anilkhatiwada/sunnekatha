from django.conf import settings
from django.db import models

from apps.catalog.models import AudioTrack
from apps.common.models import UUIDTimeStampedModel


class CreatorRole(models.TextChoices):
    NARRATOR = "narrator", "Narrator"
    EDITOR = "editor", "Editor"
    CONTENT_UPLOADER = "content_uploader", "Content uploader"
    RIGHTS_HOLDER = "rights_holder", "Rights holder"


class CreatorProfile(UUIDTimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="creator_profile",
        on_delete=models.CASCADE,
    )
    display_name = models.CharField(max_length=160)
    biography = models.TextField(blank=True)
    roles = models.JSONField(default=list)
    is_approved = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return self.display_name


class ContentContributor(UUIDTimeStampedModel):
    track = models.ForeignKey(
        AudioTrack,
        related_name="contributors",
        on_delete=models.CASCADE,
    )
    creator = models.ForeignKey(
        CreatorProfile,
        related_name="contributions",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=24, choices=CreatorRole.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("track", "creator", "role"),
                name="creator_track_role_unique",
            )
        ]


class RightsLicenseAudit(UUIDTimeStampedModel):
    track = models.ForeignKey(
        AudioTrack,
        related_name="rights_audits",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rights_license_changes",
        on_delete=models.PROTECT,
    )
    changes = models.JSONField()

    class Meta:
        ordering = ("-created_at", "id")
