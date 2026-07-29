from django.urls import path

from apps.creators.views import (
    ApprovePublishTrackView,
    CreatorDraftTrackListView,
    CreatorProcessingStatusView,
    CreatorProfileView,
    CreatorTrackAnalyticsView,
    CreatorTrackListView,
    CreatorUploadSessionListView,
    SubmitTrackReviewView,
    UpdateDraftMetadataView,
)

app_name = "creators"

urlpatterns = [
    path("profile/", CreatorProfileView.as_view(), name="profile"),
    path("tracks/", CreatorTrackListView.as_view(), name="tracks"),
    path("tracks/drafts/", CreatorDraftTrackListView.as_view(), name="drafts"),
    path("uploads/", CreatorUploadSessionListView.as_view(), name="uploads"),
    path(
        "tracks/<str:slug>/processing/",
        CreatorProcessingStatusView.as_view(),
        name="processing",
    ),
    path(
        "tracks/<str:slug>/submit/",
        SubmitTrackReviewView.as_view(),
        name="submit",
    ),
    path(
        "tracks/<str:slug>/metadata/",
        UpdateDraftMetadataView.as_view(),
        name="metadata",
    ),
    path(
        "tracks/<str:slug>/approve/",
        ApprovePublishTrackView.as_view(),
        name="approve",
    ),
    path(
        "tracks/<str:slug>/analytics/",
        CreatorTrackAnalyticsView.as_view(),
        name="analytics",
    ),
]
