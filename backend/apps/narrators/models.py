from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.common.slugs import generate_unique_slug
from apps.common.uploads import image_upload_path
from apps.common.validators import validate_image_upload


class Narrator(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="narrator_profile",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    name_ne = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)
    biography_ne = models.TextField(blank=True)
    biography_en = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    follower_count_cache = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ("name_ne", "id")
        indexes = [
            models.Index(
                fields=("is_featured", "is_verified", "name_ne"),
                name="narrator_featured_verified_idx",
            ),
            models.Index(
                fields=("-follower_count_cache", "name_ne"),
                name="narrator_followers_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name_ne, fallback="narrator")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_ne
