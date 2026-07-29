import unicodedata

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class SearchEntityType(models.TextChoices):
    TRACK = "track", "Track"
    LITERARY_WORK = "literary_work", "Literary work"
    AUTHOR = "author", "Author"
    NARRATOR = "narrator", "Narrator"
    PLAYLIST = "playlist", "Playlist"
    ALBUM = "album", "Album"
    GENRE = "genre", "Genre"
    MOOD = "mood", "Mood"


def normalize_alias(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


class SearchAlias(UUIDTimeStampedModel):
    entity_type = models.CharField(max_length=24, choices=SearchEntityType.choices)
    object_id = models.UUIDField()
    alias = models.CharField(max_length=250)
    normalized_alias = models.CharField(max_length=250, editable=False)

    class Meta:
        ordering = ("entity_type", "normalized_alias", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("entity_type", "object_id", "normalized_alias"),
                name="search_alias_entity_value_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("entity_type", "object_id"),
                name="search_alias_entity_idx",
            ),
            GinIndex(
                fields=("normalized_alias",),
                name="search_alias_trgm_idx",
                opclasses=("gin_trgm_ops",),
            ),
        ]

    def save(self, *args, **kwargs):
        self.normalized_alias = normalize_alias(self.alias)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_entity_type_display()}: {self.alias}"
