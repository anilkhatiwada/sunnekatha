from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel

ITEM_TARGET_FIELDS = (
    "track",
    "playlist",
    "album",
    "author",
    "narrator",
    "genre",
    "mood",
    "category",
)


def single_item_target_constraint():
    condition = Q()
    for index, field in enumerate(ITEM_TARGET_FIELDS):
        choice = Q(**{f"{field}__isnull": False})
        for other in ITEM_TARGET_FIELDS[index + 1 :]:
            choice &= Q(**{f"{other}__isnull": True})
        for other in ITEM_TARGET_FIELDS[:index]:
            choice &= Q(**{f"{other}__isnull": True})
        condition |= choice
    return condition


class HomeSectionType(models.TextChoices):
    HERO = "hero", "Hero"
    CONTINUE_LISTENING = "continue_listening", "Continue listening"
    TRACKS = "tracks", "Tracks"
    PLAYLISTS = "playlists", "Playlists"
    ALBUMS = "albums", "Albums"
    AUTHORS = "authors", "Authors"
    NARRATORS = "narrators", "Narrators"
    GENRES = "genres", "Genres"
    MOODS = "moods", "Moods"
    CATEGORIES = "categories", "Categories"


class HomeSectionLayout(models.TextChoices):
    RAIL = "rail", "Horizontal rail"
    GRID = "grid", "Responsive grid"


class HomeSectionSource(models.TextChoices):
    EDITORIAL = "editorial", "Selected editorial items"
    RECENT_RELEASES = "recent_releases", "Automatic new releases"


class HomeSectionQuerySet(models.QuerySet):
    def active(self, *, at=None):
        at = at or timezone.now()
        return self.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=at),
            Q(ends_at__isnull=True) | Q(ends_at__gt=at),
        )


class HomeSection(UUIDTimeStampedModel):
    identifier = models.SlugField(max_length=120, unique=True)
    title_ne = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    subtitle_ne = models.CharField(max_length=280, blank=True)
    subtitle_en = models.CharField(max_length=280, blank=True)
    section_type = models.CharField(max_length=24, choices=HomeSectionType.choices)
    content_source = models.CharField(
        max_length=24,
        choices=HomeSectionSource.choices,
        default=HomeSectionSource.EDITORIAL,
    )
    browse_category = models.ForeignKey(
        "taxonomy.ContentCategory",
        related_name="homepage_track_sections",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Optional category used by track sections for their See all link.",
    )
    layout = models.CharField(
        max_length=16,
        choices=HomeSectionLayout.choices,
        default=HomeSectionLayout.RAIL,
    )
    max_items = models.PositiveSmallIntegerField(
        default=6,
        validators=(MinValueValidator(1), MaxValueValidator(12)),
        help_text="Maximum number of visible items (1–12).",
    )
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    starts_at = models.DateTimeField(blank=True, null=True, db_index=True)
    ends_at = models.DateTimeField(blank=True, null=True, db_index=True)

    objects = HomeSectionQuerySet.as_manager()

    class Meta:
        ordering = ("sort_order", "identifier", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(starts_at__isnull=True)
                    | Q(ends_at__isnull=True)
                    | Q(ends_at__gt=models.F("starts_at"))
                ),
                name="home_section_valid_schedule",
            )
        ]

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "End time must be after start time."})
        if (
            self.content_source == HomeSectionSource.RECENT_RELEASES
            and self.section_type != HomeSectionType.TRACKS
        ):
            raise ValidationError(
                {
                    "content_source": (
                        "Automatic new releases can only be used for track sections."
                    )
                }
            )
        if self.browse_category_id and self.section_type != HomeSectionType.TRACKS:
            raise ValidationError(
                {
                    "browse_category": (
                        "A browse category can only be attached to track sections."
                    )
                }
            )
        if self.pk and HomeSection.objects.filter(pk=self.pk).exists():
            allowed = HomeSectionItem.SECTION_TARGETS[self.section_type]
            incompatible = []
            for item in self.items.all():
                selected = {
                    field
                    for field in HomeSectionItem.TARGET_FIELDS
                    if getattr(item, f"{field}_id") is not None
                }
                if not selected.issubset(allowed):
                    incompatible.extend(selected)
            if incompatible:
                raise ValidationError(
                    {
                        "section_type": (
                            "Existing items are incompatible with this section type."
                        )
                    }
                )

    def __str__(self):
        return self.title_ne


class HomeSectionItem(UUIDTimeStampedModel):
    section = models.ForeignKey(
        HomeSection, related_name="items", on_delete=models.CASCADE
    )
    track = models.ForeignKey(
        "catalog.AudioTrack",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    playlist = models.ForeignKey(
        "playlists.Playlist",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    album = models.ForeignKey(
        "catalog.Album",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    author = models.ForeignKey(
        "authors.Author",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    narrator = models.ForeignKey(
        "narrators.Narrator",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    genre = models.ForeignKey(
        "taxonomy.Genre",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    mood = models.ForeignKey(
        "taxonomy.Mood",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        "taxonomy.ContentCategory",
        related_name="home_section_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    position = models.PositiveIntegerField()

    TARGET_FIELDS = ITEM_TARGET_FIELDS
    SECTION_TARGETS = {
        HomeSectionType.TRACKS: {"track"},
        HomeSectionType.PLAYLISTS: {"playlist"},
        HomeSectionType.ALBUMS: {"album"},
        HomeSectionType.AUTHORS: {"author"},
        HomeSectionType.NARRATORS: {"narrator"},
        HomeSectionType.GENRES: {"genre"},
        HomeSectionType.MOODS: {"mood"},
        HomeSectionType.CATEGORIES: {"category"},
        HomeSectionType.HERO: {"track", "playlist", "album"},
        HomeSectionType.CONTINUE_LISTENING: set(),
    }

    class Meta:
        ordering = ("position", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("section", "position"),
                name="home_section_item_unique_position",
            ),
            models.CheckConstraint(
                condition=single_item_target_constraint(),
                name="home_section_item_exactly_one_target",
            ),
        ]

    def clean(self):
        super().clean()
        selected = {
            field
            for field in self.TARGET_FIELDS
            if getattr(self, f"{field}_id") is not None
        }
        if len(selected) != 1:
            raise ValidationError("Select exactly one homepage item target.")
        if self.section_id:
            allowed = self.SECTION_TARGETS[self.section.section_type]
            if not selected.issubset(allowed):
                raise ValidationError(
                    {
                        next(iter(selected)): (
                            f"{next(iter(selected)).title()} items are not valid for "
                            f"{self.section.get_section_type_display()} sections."
                        )
                    }
                )

    def __str__(self):
        target = next(
            (
                getattr(self, field)
                for field in self.TARGET_FIELDS
                if getattr(self, f"{field}_id") is not None
            ),
            "Unconfigured item",
        )
        return f"{self.section}: {self.position} — {target}"
