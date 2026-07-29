from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.authors.models import Author
from apps.catalog.models import AudioTrack
from apps.common.models import UUIDTimeStampedModel
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist


class FavoriteTrack(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="favorite_tracks",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="favorited_by",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "track"),
                name="library_unique_favorite_track",
            )
        ]
        indexes = [
            models.Index(
                fields=("user", "-created_at"),
                name="library_favorite_recent_idx",
            )
        ]


class SavedPlaylist(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="saved_playlists",
        on_delete=models.CASCADE,
    )
    playlist = models.ForeignKey(
        Playlist,
        related_name="saved_by",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "playlist"),
                name="library_unique_saved_playlist",
            )
        ]
        indexes = [
            models.Index(
                fields=("user", "-created_at"),
                name="library_saved_recent_idx",
            )
        ]


class FollowedAuthor(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="followed_authors",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        Author,
        related_name="followers",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "author"),
                name="library_unique_followed_author",
            )
        ]
        indexes = [
            models.Index(
                fields=("user", "-created_at"),
                name="library_author_recent_idx",
            )
        ]


class FollowedNarrator(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="followed_narrators",
        on_delete=models.CASCADE,
    )
    narrator = models.ForeignKey(
        Narrator,
        related_name="followers",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "narrator"),
                name="library_unique_followed_narrator",
            )
        ]
        indexes = [
            models.Index(
                fields=("user", "-created_at"),
                name="library_narrator_recent_idx",
            )
        ]


class ListeningProgress(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="listening_progress",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="listening_progress",
        on_delete=models.CASCADE,
    )
    position_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    duration_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_completed = models.BooleanField(default=False, db_index=True)
    last_listened_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-last_listened_at", "-updated_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "track"),
                name="library_unique_listening_progress",
            ),
            models.CheckConstraint(
                condition=models.Q(position_seconds__gte=0),
                name="library_progress_position_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_seconds__gt=0),
                name="library_progress_duration_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(position_seconds__lte=models.F("duration_seconds")),
                name="library_progress_position_within_duration",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(progress_percentage__gte=0)
                    & models.Q(progress_percentage__lte=100)
                ),
                name="library_progress_percentage_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "is_completed", "-last_listened_at"),
                name="library_continue_listening_idx",
            )
        ]


class PlaybackEventType(models.TextChoices):
    STARTED = "started", "Started"
    RESUMED = "resumed", "Resumed"
    PAUSED = "paused", "Paused"
    SEEKED = "seeked", "Seeked"
    COMPLETED = "completed", "Completed"
    STOPPED = "stopped", "Stopped"
    ERROR = "error", "Error"


class QueueRepeatMode(models.TextChoices):
    OFF = "off", "Off"
    ONE = "one", "One"
    ALL = "all", "All"


class PlaybackSession(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="playback_sessions",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="playback_sessions",
        on_delete=models.CASCADE,
    )
    device_id = models.CharField(max_length=128)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(blank=True, null=True, db_index=True)
    listened_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    completed = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-started_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(listened_seconds__gte=0),
                name="library_session_listened_nonnegative",
            ),
            models.UniqueConstraint(
                fields=("user", "track", "device_id"),
                condition=models.Q(ended_at__isnull=True),
                name="library_unique_active_playback_session",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "-last_activity_at"),
                name="library_session_activity_idx",
            )
        ]


class ListeningHistory(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="listening_history",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="listening_history",
        on_delete=models.CASCADE,
    )
    first_listened_at = models.DateTimeField()
    last_listened_at = models.DateTimeField(db_index=True)
    total_listened_seconds = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    play_count = models.PositiveIntegerField(default=0)
    completion_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-last_listened_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "track"),
                name="library_unique_listening_history",
            )
        ]
        indexes = [
            models.Index(
                fields=("user", "-last_listened_at"),
                name="library_history_recent_idx",
            )
        ]


class PlaybackEvent(UUIDTimeStampedModel):
    session = models.ForeignKey(
        PlaybackSession,
        related_name="events",
        on_delete=models.CASCADE,
    )
    event_type = models.CharField(
        max_length=16,
        choices=PlaybackEventType.choices,
    )
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    position_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    deduplication_key = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("occurred_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(position_seconds__isnull=True)
                    | models.Q(position_seconds__gte=0)
                ),
                name="library_event_position_nonnegative",
            ),
            models.UniqueConstraint(
                fields=("session", "deduplication_key"),
                condition=~models.Q(deduplication_key=""),
                name="library_unique_session_event_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=("session", "event_type", "-occurred_at"),
                name="library_event_session_type_idx",
            )
        ]


class UserQueue(UUIDTimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="queue",
        on_delete=models.CASCADE,
    )
    current_index = models.IntegerField(default=-1)
    position_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_shuffle_enabled = models.BooleanField(default=False)
    repeat_mode = models.CharField(
        max_length=8,
        choices=QueueRepeatMode.choices,
        default=QueueRepeatMode.OFF,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_index__gte=-1),
                name="library_queue_current_index_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(position_seconds__gte=0),
                name="library_queue_position_nonnegative",
            ),
        ]


class UserQueueItem(UUIDTimeStampedModel):
    queue = models.ForeignKey(
        UserQueue,
        related_name="items",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="queue_items",
        on_delete=models.CASCADE,
    )
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ("position", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("queue", "position"),
                name="library_unique_queue_position",
            )
        ]
        indexes = [
            models.Index(
                fields=("queue", "position"),
                name="library_queue_item_order_idx",
            )
        ]
