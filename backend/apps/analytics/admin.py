import csv
from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from unfold.admin import ModelAdmin

from apps.analytics.dashboard import (
    AnalyticsDateRange,
    admin_analytics_dashboard_service,
)
from apps.analytics.models import (
    DailyAuthorMetric,
    DailyNarratorMetric,
    DailyPlatformMetric,
    DailyPlaylistMetric,
    DailyTrackMetric,
)
from apps.common.admin import ProtectedDeleteAdminMixin


class DailyMetricAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "date",
        "content_entity",
        "total_plays",
        "unique_listeners",
        "listening_seconds",
        "completed_plays",
    )
    list_filter = ("date",)
    date_hierarchy = "date"
    readonly_fields = (
        "id",
        "date",
        "total_plays",
        "unique_listeners",
        "listening_seconds",
        "completed_plays",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Content")
    def content_entity(self, obj):
        for field in ("track", "author", "narrator", "playlist"):
            if hasattr(obj, f"{field}_id"):
                return getattr(obj, field)
        return "Platform"


def analytics_date_range(request):
    today = timezone.localdate()
    preset = request.GET.get("range", "30_days")
    ranges = {
        "today": AnalyticsDateRange(today, today, "today", "Today"),
        "7_days": AnalyticsDateRange(
            today - timedelta(days=6),
            today,
            "7_days",
            "Last 7 days",
        ),
        "30_days": AnalyticsDateRange(
            today - timedelta(days=29),
            today,
            "30_days",
            "Last 30 days",
        ),
        "current_month": AnalyticsDateRange(
            today.replace(day=1),
            today,
            "current_month",
            "Current month",
        ),
    }
    if preset != "custom":
        return ranges.get(preset, ranges["30_days"]), None
    start = parse_date(request.GET.get("start", ""))
    end = parse_date(request.GET.get("end", ""))
    if not start or not end:
        return ranges["30_days"], "Select valid start and end dates."
    if start > end:
        return ranges["30_days"], "Start date cannot be after end date."
    if (end - start).days > 366:
        return ranges["30_days"], "Custom ranges are limited to 366 days."
    return AnalyticsDateRange(start, end, "custom", f"{start} to {end}"), None


@admin.register(DailyPlatformMetric)
class DailyPlatformMetricAdmin(DailyMetricAdmin):
    def get_urls(self):
        return [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="analytics_dashboard",
            ),
            path(
                "dashboard/export.csv",
                self.admin_site.admin_view(self.export_dashboard_csv),
                name="analytics_dashboard_export",
            ),
        ] + super().get_urls()

    def _require_dashboard_access(self, request):
        if not request.user.has_perm("analytics.view_dailyplatformmetric"):
            raise PermissionDenied

    def dashboard_view(self, request):
        self._require_dashboard_access(request)
        date_range, error = analytics_date_range(request)
        data = admin_analytics_dashboard_service.get(date_range=date_range)
        context = {
            **self.admin_site.each_context(request),
            "title": "Listening analytics",
            "opts": self.model._meta,
            "date_range": date_range,
            "date_error": error,
            "analytics": data,
            "can_export": request.user.has_perm("analytics.export_analytics_dashboard"),
            "export_url": reverse("admin:analytics_dashboard_export"),
        }
        return TemplateResponse(
            request,
            "admin/analytics/dashboard.html",
            context,
        )

    def export_dashboard_csv(self, request):
        self._require_dashboard_access(request)
        if not request.user.has_perm("analytics.export_analytics_dashboard"):
            raise PermissionDenied
        date_range, error = analytics_date_range(request)
        if error:
            raise PermissionDenied("Invalid analytics date range.")
        data = admin_analytics_dashboard_service.get(date_range=date_range)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="sunnekatha-analytics-'
            f'{date_range.start}-{date_range.end}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(("SunneKatha aggregate analytics", date_range.label))
        writer.writerow(("Metric", "Value", "Note"))
        for card in data["cards"]:
            writer.writerow((card["label"], card["value"], card["note"]))
        for ranking in data["rankings"]:
            writer.writerow(())
            writer.writerow((ranking["title"], "Plays", "Listening hours"))
            for row in ranking["rows"]:
                writer.writerow((row["label"], row["plays"], row["listening_hours"]))
        return response


@admin.register(DailyTrackMetric)
class DailyTrackMetricAdmin(DailyMetricAdmin):
    list_select_related = ("track",)
    search_fields = ("track__title_ne", "track__title_en")
    readonly_fields = DailyMetricAdmin.readonly_fields + ("track",)


@admin.register(DailyAuthorMetric)
class DailyAuthorMetricAdmin(DailyMetricAdmin):
    list_select_related = ("author",)
    search_fields = ("author__name_ne", "author__name_en")
    readonly_fields = DailyMetricAdmin.readonly_fields + ("author",)


@admin.register(DailyNarratorMetric)
class DailyNarratorMetricAdmin(DailyMetricAdmin):
    list_select_related = ("narrator",)
    search_fields = ("narrator__name_ne", "narrator__name_en")
    readonly_fields = DailyMetricAdmin.readonly_fields + ("narrator",)


@admin.register(DailyPlaylistMetric)
class DailyPlaylistMetricAdmin(DailyMetricAdmin):
    list_select_related = ("playlist",)
    search_fields = ("playlist__title_ne", "playlist__title_en")
    readonly_fields = DailyMetricAdmin.readonly_fields + ("playlist",)
