from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TypedDict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import (
    DailyAuthorMetric,
    DailyNarratorMetric,
    DailyPlatformMetric,
    DailyPlaylistMetric,
    DailyTrackMetric,
)


@dataclass(frozen=True)
class AnalyticsDateRange:
    start: date
    end: date
    identifier: str
    label: str


class MetricCard(TypedDict):
    label: str
    value: str
    note: str


class RankingRow(TypedDict):
    label: str
    plays: int
    listening_hours: str
    url: str


class AnalyticsDashboardData(TypedDict):
    cards: list[MetricCard]
    rankings: list[dict]
    latest_aggregate_date: date | None
    is_delayed: bool
    unique_listener_note: str
    premium_conversion_note: str


def _hours(seconds):
    return f"{(Decimal(seconds or 0) / Decimal('3600')):.1f}"


def _change_url(app_label, model_name, object_id):
    return reverse(
        f"admin:{app_label}_{model_name}_change",
        args=(object_id,),
    )


class AdminAnalyticsDashboardService:
    """Read-only reporting over daily aggregate tables, never raw playback events."""

    ranking_limit = 10

    def get(self, *, date_range: AnalyticsDateRange) -> AnalyticsDashboardData:
        today = timezone.localdate()
        week_start = today - timedelta(days=6)
        month_start = today.replace(day=1)
        zero = Value(Decimal("0"), output_field=DecimalField())
        platform = DailyPlatformMetric.objects.aggregate(
            today_seconds=Coalesce(
                Sum("listening_seconds", filter=Q(date=today)),
                zero,
            ),
            week_seconds=Coalesce(
                Sum("listening_seconds", filter=Q(date__range=(week_start, today))),
                zero,
            ),
            month_seconds=Coalesce(
                Sum(
                    "listening_seconds",
                    filter=Q(date__range=(month_start, today)),
                ),
                zero,
            ),
            selected_plays=Coalesce(
                Sum(
                    "total_plays",
                    filter=Q(date__range=(date_range.start, date_range.end)),
                ),
                0,
            ),
            selected_unique=Coalesce(
                Sum(
                    "unique_listeners",
                    filter=Q(date__range=(date_range.start, date_range.end)),
                ),
                0,
            ),
            selected_completed=Coalesce(
                Sum(
                    "completed_plays",
                    filter=Q(date__range=(date_range.start, date_range.end)),
                ),
                0,
            ),
        )
        plays = int(platform["selected_plays"])
        completed = int(platform["selected_completed"])
        completion_rate = (Decimal(completed) / Decimal(plays) * 100) if plays else 0
        latest = (
            DailyPlatformMetric.objects.order_by("-date")
            .values_list("date", flat=True)
            .first()
        )

        cards: list[MetricCard] = [
            {
                "label": "Listening hours today",
                "value": _hours(platform["today_seconds"]),
                "note": "Provisional until the daily aggregate completes.",
            },
            {
                "label": "Listening hours this week",
                "value": _hours(platform["week_seconds"]),
                "note": "From daily aggregate tables.",
            },
            {
                "label": "Listening hours this month",
                "value": _hours(platform["month_seconds"]),
                "note": "From daily aggregate tables.",
            },
            {
                "label": "Total plays",
                "value": f"{plays:,}",
                "note": date_range.label,
            },
            {
                "label": "Summed daily unique listeners",
                "value": f"{int(platform['selected_unique']):,}",
                "note": (
                    "A listener active on multiple days may be counted more than once."
                ),
            },
            {
                "label": "Completion rate",
                "value": f"{completion_rate:.1f}%",
                "note": "Completed plays divided by total plays.",
            },
            {
                "label": "New users",
                "value": f"{self._new_users(date_range):,}",
                "note": "Account registrations; no listening details included.",
            },
            {
                "label": "Premium conversions",
                "value": "Unavailable",
                "note": "No aggregate conversion event is recorded yet.",
            },
        ]
        rankings = [
            self._track_rankings(date_range),
            self._work_rankings(date_range),
            self._entity_rankings(
                date_range,
                model=DailyAuthorMetric,
                relation="author",
                app_label="authors",
                model_name="author",
                title="Popular authors",
                label_field="author__name_ne",
            ),
            self._entity_rankings(
                date_range,
                model=DailyNarratorMetric,
                relation="narrator",
                app_label="narrators",
                model_name="narrator",
                title="Popular narrators",
                label_field="narrator__name_ne",
            ),
            self._entity_rankings(
                date_range,
                model=DailyPlaylistMetric,
                relation="playlist",
                app_label="playlists",
                model_name="playlist",
                title="Popular playlists",
                label_field="playlist__title_ne",
            ),
        ]
        return {
            "cards": cards,
            "rankings": rankings,
            "latest_aggregate_date": latest,
            "is_delayed": latest is None or latest < today - timedelta(days=1),
            "unique_listener_note": (
                "Unique listeners are daily aggregate sums, not cross-period "
                "deduplicated user counts."
            ),
            "premium_conversion_note": (
                "Premium conversion reporting is unavailable until a dedicated "
                "aggregate is introduced."
            ),
        }

    def _new_users(self, date_range):
        start = timezone.make_aware(datetime.combine(date_range.start, time.min))
        end = timezone.make_aware(
            datetime.combine(
                date_range.end + timedelta(days=1),
                time.min,
            )
        )
        return (
            get_user_model()
            .objects.filter(
                created_at__gte=start,
                created_at__lt=end,
            )
            .count()
        )

    def _track_rankings(self, date_range):
        rows = (
            DailyTrackMetric.objects.filter(
                date__range=(date_range.start, date_range.end)
            )
            .values("track_id", "track__title_ne")
            .annotate(
                plays=Sum("total_plays"),
                seconds=Sum("listening_seconds"),
                listeners=Sum("unique_listeners"),
            )
            .filter(listeners__gte=settings.ANALYTICS_PRIVACY_MIN_LISTENERS)
            .order_by("-plays", "track__title_ne")[: self.ranking_limit]
        )
        return {
            "identifier": "tracks",
            "title": "Most-played tracks",
            "rows": [
                self._row(
                    row,
                    label=row["track__title_ne"],
                    url=_change_url("catalog", "audiotrack", row["track_id"]),
                )
                for row in rows
            ],
        }

    def _work_rankings(self, date_range):
        rows = (
            DailyTrackMetric.objects.filter(
                date__range=(date_range.start, date_range.end)
            )
            .values("track__work_id", "track__work__title_ne")
            .annotate(
                plays=Sum("total_plays"),
                seconds=Sum("listening_seconds"),
                listeners=Sum("unique_listeners"),
            )
            .filter(listeners__gte=settings.ANALYTICS_PRIVACY_MIN_LISTENERS)
            .order_by("-plays", "track__work__title_ne")[: self.ranking_limit]
        )
        return {
            "identifier": "works",
            "title": "Most-played literary works",
            "rows": [
                self._row(
                    row,
                    label=row["track__work__title_ne"],
                    url=_change_url(
                        "catalog",
                        "literarywork",
                        row["track__work_id"],
                    ),
                )
                for row in rows
            ],
        }

    def _entity_rankings(
        self,
        date_range,
        *,
        model,
        relation,
        app_label,
        model_name,
        title,
        label_field,
    ):
        id_field = f"{relation}_id"
        rows = (
            model.objects.filter(date__range=(date_range.start, date_range.end))
            .values(id_field, label_field)
            .annotate(
                plays=Sum("total_plays"),
                seconds=Sum("listening_seconds"),
                listeners=Sum("unique_listeners"),
            )
            .filter(listeners__gte=settings.ANALYTICS_PRIVACY_MIN_LISTENERS)
            .order_by("-plays", label_field)[: self.ranking_limit]
        )
        return {
            "identifier": relation,
            "title": title,
            "rows": [
                self._row(
                    row,
                    label=row[label_field],
                    url=_change_url(app_label, model_name, row[id_field]),
                )
                for row in rows
            ],
        }

    @staticmethod
    def _row(row, *, label, url) -> RankingRow:
        return {
            "label": label,
            "plays": int(row["plays"] or 0),
            "listening_hours": _hours(row["seconds"]),
            "url": url,
        }


admin_analytics_dashboard_service = AdminAnalyticsDashboardService()
