from django.urls import path

from apps.explore.views import ExploreTrackListView, ExploreView

app_name = "explore"

urlpatterns = [
    path("explore/", ExploreView.as_view(), name="detail"),
    path("explore/tracks/", ExploreTrackListView.as_view(), name="track-list"),
]
