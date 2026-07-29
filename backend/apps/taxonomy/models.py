from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.common.slugs import generate_unique_slug
from apps.common.uploads import image_upload_path
from apps.common.validators import validate_image_upload


class TaxonomyBase(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=160, unique=True, allow_unicode=True)
    name_ne = models.CharField(max_length=160)
    name_en = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ("sort_order", "name_ne", "id")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                self.name_ne,
                fallback=self._meta.model_name,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_ne


class Genre(TaxonomyBase):
    pass


class Mood(TaxonomyBase):
    pass


class Language(TaxonomyBase):
    pass


class ContentCategory(TaxonomyBase):
    class Meta(TaxonomyBase.Meta):
        verbose_name_plural = "Content categories"
