from django.urls import path

from apps.playlists.views import (
    AddTrackView,
    AddWorkView,
    ChangeVisibilityView,
    DuplicatePlaylistView,
    FeaturedPlaylistListView,
    PlaylistDetailView,
    PlaylistListCreateView,
    RemoveTrackView,
    RemoveWorkView,
    ReorderTracksView,
)

app_name = "playlists"

urlpatterns = [
    path("", PlaylistListCreateView.as_view(), name="list-create"),
    path("featured/", FeaturedPlaylistListView.as_view(), name="featured"),
    path("<str:slug>/tracks/add/", AddTrackView.as_view(), name="add-track"),
    path("<str:slug>/tracks/remove/", RemoveTrackView.as_view(), name="remove-track"),
    path("<str:slug>/works/add/", AddWorkView.as_view(), name="add-work"),
    path("<str:slug>/works/remove/", RemoveWorkView.as_view(), name="remove-work"),
    path("<str:slug>/tracks/reorder/", ReorderTracksView.as_view(), name="reorder"),
    path(
        "<str:slug>/visibility/",
        ChangeVisibilityView.as_view(),
        name="visibility",
    ),
    path("<str:slug>/duplicate/", DuplicatePlaylistView.as_view(), name="duplicate"),
    path("<str:slug>/", PlaylistDetailView.as_view(), name="detail"),
]
