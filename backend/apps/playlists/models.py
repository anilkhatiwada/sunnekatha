import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.models import AudioTrack
from apps.common.models import UUIDTimeStampedModel
from apps.common.slugs import generate_unique_slug
from apps.common.uploads import image_upload_path
from apps.common.validators import validate_image_upload


class PlaylistType(models.TextChoices):
    EDITORIAL = "editorial", "Editorial"
    USER = "user", "User"
    AUTOMATIC = "automatic", "Automatic"


class PlaylistVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    UNLISTED = "unlisted", "Unlisted"
    PRIVATE = "private", "Private"


class Playlist(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=220, unique=True, allow_unicode=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="playlists",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    title_ne = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250, blank=True)
    description_ne = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    playlist_type = models.CharField(
        max_length=16,
        choices=PlaylistType.choices,
        default=PlaylistType.USER,
        db_index=True,
    )
    visibility = models.CharField(
        max_length=16,
        choices=PlaylistVisibility.choices,
        default=PlaylistVisibility.PRIVATE,
        db_index=True,
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    tracks = models.ManyToManyField(
        AudioTrack,
        through="PlaylistItem",
        related_name="playlists",
    )

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        playlist_type=PlaylistType.USER,
                        owner__isnull=False,
                    )
                    | (
                        ~models.Q(playlist_type=PlaylistType.USER)
                        & models.Q(owner__isnull=True)
                    )
                ),
                name="playlist_type_owner_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_featured=False)
                    | models.Q(playlist_type=PlaylistType.EDITORIAL)
                ),
                name="playlist_featured_editorial_only",
            ),
        ]
        indexes = [
            models.Index(
                fields=("visibility", "is_published", "-created_at"),
                name="playlist_public_idx",
            ),
            models.Index(
                fields=("is_featured", "visibility", "is_published"),
                name="playlist_featured_idx",
            ),
            models.Index(
                fields=("owner", "playlist_type", "-updated_at"),
                name="playlist_owner_type_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.playlist_type == PlaylistType.USER and self.owner_id is None:
            raise ValidationError({"owner": "User playlists require an owner."})
        if self.playlist_type != PlaylistType.USER and self.owner_id is not None:
            raise ValidationError(
                {"owner": "Editorial and automatic playlists cannot have an owner."}
            )
        if self.is_featured and self.playlist_type != PlaylistType.EDITORIAL:
            raise ValidationError(
                {"is_featured": "Only editorial playlists can be featured."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title_ne, fallback="playlist")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ne


class PlaylistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist,
        related_name="items",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="playlist_items",
        on_delete=models.CASCADE,
    )
    position = models.PositiveIntegerField(db_index=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="playlist_items_added",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("playlist", "track"),
                name="playlist_unique_track",
            ),
            models.UniqueConstraint(
                fields=("playlist", "position"),
                name="playlist_unique_position",
            ),
        ]
        indexes = [
            models.Index(
                fields=("playlist", "position"),
                name="playlist_item_order_idx",
            )
        ]

    def __str__(self):
        return f"{self.playlist}: {self.position} — {self.track}"
