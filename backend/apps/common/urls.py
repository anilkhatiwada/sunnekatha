from django.urls import path

from apps.common.views import (
    ApplicationVersionView,
    HealthCheckView,
    ReadinessCheckView,
)

app_name = "common"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("readiness/", ReadinessCheckView.as_view(), name="readiness"),
    path("version/", ApplicationVersionView.as_view(), name="version"),
]
