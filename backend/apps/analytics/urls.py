from django.urls import path

from apps.analytics.views import (
    AnalyticsDailyView,
    AnalyticsPopularView,
    AnalyticsSummaryView,
)

app_name = "analytics"

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="summary"),
    path("daily/", AnalyticsDailyView.as_view(), name="daily"),
    path("popular/", AnalyticsPopularView.as_view(), name="popular"),
]
