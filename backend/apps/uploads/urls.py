from django.urls import path

from apps.uploads.views import (
    CancelUploadView,
    ConfirmUploadView,
    RequestUploadView,
    UploadStatusView,
)

app_name = "uploads"

urlpatterns = [
    path("", RequestUploadView.as_view(), name="request"),
    path("<uuid:session_id>/", UploadStatusView.as_view(), name="status"),
    path(
        "<uuid:session_id>/confirm/",
        ConfirmUploadView.as_view(),
        name="confirm",
    ),
    path(
        "<uuid:session_id>/cancel/",
        CancelUploadView.as_view(),
        name="cancel",
    ),
]
