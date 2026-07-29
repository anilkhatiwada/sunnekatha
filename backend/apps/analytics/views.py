from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.analytics.models import (
    DailyAuthorMetric,
    DailyNarratorMetric,
    DailyPlatformMetric,
    DailyPlaylistMetric,
    DailyTrackMetric,
)
from apps.analytics.permissions import IsActiveStaff
from apps.analytics.serializers import (
    AnalyticsDateRangeSerializer,
    DailyMetricSerializer,
    MetricTotalsSerializer,
    PopularMetricSerializer,
)

ZERO = Decimal("0")


def aggregate_values(queryset):
    values = queryset.aggregate(
        total_plays=Coalesce(Sum("total_plays"), 0),
        unique_listeners=Coalesce(Sum("unique_listeners"), 0),
        listening_seconds=Coalesce(Sum("listening_seconds"), ZERO),
        completed_plays=Coalesce(Sum("completed_plays"), 0),
    )
    return metric_payload(values)


def metric_payload(values):
    plays = values["total_plays"] or 0
    return {
        "totalPlays": plays,
        "uniqueListeners": values["unique_listeners"] or 0,
        "listeningHours": (values["listening_seconds"] or ZERO) / Decimal(3600),
        "completionRate": (
            Decimal(values["completed_plays"] or 0) * Decimal(100) / Decimal(plays)
            if plays
            else ZERO
        ),
    }


class AnalyticsBaseView(GenericAPIView):
    permission_classes = [IsActiveStaff]
    serializer_class = AnalyticsDateRangeSerializer

    def get_parameters(self):
        serializer = self.get_serializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        today = timezone.localdate()
        date_to = serializer.validated_data.get("dateTo", today)
        date_from = serializer.validated_data.get(
            "dateFrom",
            date_to - timedelta(days=29),
        )
        if (date_to - date_from).days > settings.ANALYTICS_MAX_RANGE_DAYS:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"dateTo": "Requested analytics range is too large."})
        return date_from, date_to, serializer.validated_data.get("limit", 10)


class AnalyticsSummaryView(AnalyticsBaseView):
    output_serializer_class = MetricTotalsSerializer

    def get(self, request):
        del request
        date_from, date_to, _ = self.get_parameters()
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "uniqueListenerAggregation": "sum_of_daily_unique_listeners",
            **aggregate_values(
                DailyPlatformMetric.objects.filter(date__range=(date_from, date_to))
            ),
        }
        return Response(payload)


class AnalyticsDailyView(AnalyticsBaseView):
    output_serializer_class = DailyMetricSerializer

    def get(self, request):
        del request
        date_from, date_to, _ = self.get_parameters()
        rows = DailyPlatformMetric.objects.filter(
            date__range=(date_from, date_to)
        ).order_by("date")
        return Response(
            [{"date": row.date, **metric_payload(row.__dict__)} for row in rows]
        )


class AnalyticsPopularView(AnalyticsBaseView):
    output_serializer_class = PopularMetricSerializer
    models = (
        (
            "tracks",
            DailyTrackMetric,
            "track",
            "track__slug",
            "track__title_ne",
        ),
        (
            "authors",
            DailyAuthorMetric,
            "author",
            "author__slug",
            "author__name_ne",
        ),
        (
            "narrators",
            DailyNarratorMetric,
            "narrator",
            "narrator__slug",
            "narrator__name_ne",
        ),
        (
            "playlists",
            DailyPlaylistMetric,
            "playlist",
            "playlist__slug",
            "playlist__title_ne",
        ),
    )

    def get(self, request):
        del request
        date_from, date_to, limit = self.get_parameters()
        payload = {}
        for key, model, entity, slug_field, name_field in self.models:
            rows = (
                model.objects.filter(date__range=(date_from, date_to))
                .values(f"{entity}_id", slug_field, name_field)
                .annotate(
                    total_plays=Sum("total_plays"),
                    unique_listener_days=Sum("unique_listeners"),
                    listening_seconds=Sum("listening_seconds"),
                    completed_plays=Sum("completed_plays"),
                    peak_unique_listeners=Max("unique_listeners"),
                )
                .filter(
                    peak_unique_listeners__gte=(
                        settings.ANALYTICS_PRIVACY_MIN_LISTENERS
                    )
                )
                .order_by("-total_plays", f"{entity}_id")[:limit]
            )
            payload[key] = [
                {
                    "id": row[f"{entity}_id"],
                    "slug": row[slug_field],
                    "name": row[name_field],
                    **metric_payload(
                        {
                            **row,
                            "unique_listeners": row["unique_listener_days"],
                        }
                    ),
                }
                for row in rows
            ]
        payload["uniqueListenerAggregation"] = "sum_of_daily_unique_listeners"
        return Response(payload)
