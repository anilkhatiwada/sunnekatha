from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.analytics.models import (
    DailyAuthorMetric,
    DailyNarratorMetric,
    DailyPlatformMetric,
    DailyPlaylistMetric,
    DailyTrackMetric,
)
from apps.library.models import PlaybackSession


class DailyAnalyticsAggregationService:
    metric_fields = {
        "total_plays": Count("id"),
        "unique_listeners": Count("user_id", distinct=True),
        "listening_seconds": Coalesce(
            Sum("listened_seconds"),
            Decimal("0"),
        ),
        "completed_plays": Count("id", filter=models.Q(completed=True)),
    }

    @transaction.atomic
    def aggregate(self, metric_date):
        start = timezone.make_aware(datetime.combine(metric_date, time.min))
        end = start + timedelta(days=1)
        sessions = PlaybackSession.objects.filter(
            started_at__gte=start,
            started_at__lt=end,
        )
        platform = sessions.aggregate(**self.metric_fields)
        DailyPlatformMetric.objects.update_or_create(
            date=metric_date,
            defaults=platform,
        )
        self._replace(
            DailyTrackMetric,
            "track_id",
            sessions.values("track_id").annotate(**self.metric_fields),
            metric_date,
        )
        self._replace(
            DailyAuthorMetric,
            "author_id",
            sessions.values(author_id=models.F("track__work__author_id")).annotate(
                **self.metric_fields
            ),
            metric_date,
        )
        self._replace(
            DailyNarratorMetric,
            "narrator_id",
            sessions.values(narrator_id=models.F("track__narrator_id")).annotate(
                **self.metric_fields
            ),
            metric_date,
        )
        playlist_sessions = sessions.filter(
            track__playlist_items__playlist__is_published=True
        )
        self._replace(
            DailyPlaylistMetric,
            "playlist_id",
            playlist_sessions.values(
                playlist_id=models.F("track__playlist_items__playlist_id")
            ).annotate(**self.metric_fields),
            metric_date,
        )
        return DailyPlatformMetric.objects.get(date=metric_date)

    @staticmethod
    def _replace(model, entity_field, rows, metric_date):
        model.objects.filter(date=metric_date).delete()
        model.objects.bulk_create(
            [
                model(
                    date=metric_date,
                    **{entity_field: row[entity_field]},
                    total_plays=row["total_plays"],
                    unique_listeners=row["unique_listeners"],
                    listening_seconds=row["listening_seconds"],
                    completed_plays=row["completed_plays"],
                )
                for row in rows
            ]
        )


daily_analytics_aggregation_service = DailyAnalyticsAggregationService()
