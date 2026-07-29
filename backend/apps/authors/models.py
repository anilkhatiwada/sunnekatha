from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.common.slugs import generate_unique_slug
from apps.common.uploads import image_upload_path
from apps.common.validators import validate_image_upload


class Author(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    name_ne = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)
    biography_ne = models.TextField(blank=True)
    biography_en = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    birth_date = models.DateField(blank=True, null=True)
    death_date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100, default="Nepal")
    is_featured = models.BooleanField(default=False, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("name_ne", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(birth_date__isnull=True)
                    | models.Q(death_date__isnull=True)
                    | models.Q(death_date__gte=models.F("birth_date"))
                ),
                name="author_death_not_before_birth",
            )
        ]
        indexes = [
            models.Index(
                fields=("is_featured", "is_verified", "name_ne"),
                name="author_featured_verified_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.birth_date and self.death_date and self.death_date < self.birth_date:
            raise ValidationError(
                {"death_date": "Death date cannot precede birth date."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name_ne, fallback="author")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_ne
