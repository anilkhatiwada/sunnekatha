from django.db import models

from apps.common.models import UUIDTimeStampedModel


class DailyMetricBase(UUIDTimeStampedModel):
    date = models.DateField(db_index=True)
    total_plays = models.PositiveBigIntegerField(default=0)
    unique_listeners = models.PositiveBigIntegerField(default=0)
    listening_seconds = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )
    completed_plays = models.PositiveBigIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ("-date", "id")


class DailyPlatformMetric(DailyMetricBase):
    class Meta(DailyMetricBase.Meta):
        permissions = [
            (
                "export_analytics_dashboard",
                "Can export aggregate analytics dashboard data",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("date",),
                name="analytics_unique_platform_date",
            )
        ]

    def __str__(self):
        return f"Platform — {self.date}"


class DailyTrackMetric(DailyMetricBase):
    track = models.ForeignKey(
        "catalog.AudioTrack",
        related_name="daily_metrics",
        on_delete=models.CASCADE,
    )

    class Meta(DailyMetricBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("date", "track"),
                name="analytics_unique_track_date",
            )
        ]
        indexes = [
            models.Index(
                fields=("date", "-total_plays"),
                name="analytics_track_popular_idx",
            )
        ]

    def __str__(self):
        return f"{self.track} — {self.date}"


class DailyAuthorMetric(DailyMetricBase):
    author = models.ForeignKey(
        "authors.Author",
        related_name="daily_metrics",
        on_delete=models.CASCADE,
    )

    class Meta(DailyMetricBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("date", "author"),
                name="analytics_unique_author_date",
            )
        ]
        indexes = [
            models.Index(
                fields=("date", "-total_plays"),
                name="analytics_author_popular_idx",
            )
        ]


class DailyNarratorMetric(DailyMetricBase):
    narrator = models.ForeignKey(
        "narrators.Narrator",
        related_name="daily_metrics",
        on_delete=models.CASCADE,
    )

    class Meta(DailyMetricBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("date", "narrator"),
                name="analytics_unique_narrator_date",
            )
        ]
        indexes = [
            models.Index(
                fields=("date", "-total_plays"),
                name="analytics_narrator_pop_idx",
            )
        ]


class DailyPlaylistMetric(DailyMetricBase):
    playlist = models.ForeignKey(
        "playlists.Playlist",
        related_name="daily_metrics",
        on_delete=models.CASCADE,
    )

    class Meta(DailyMetricBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("date", "playlist"),
                name="analytics_unique_playlist_date",
            )
        ]
        indexes = [
            models.Index(
                fields=("date", "-total_plays"),
                name="analytics_playlist_pop_idx",
            )
        ]
