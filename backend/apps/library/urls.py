from django.urls import path

from apps.library.views import (
    FavoriteTrackListView,
    FavoriteTrackView,
    FollowAuthorView,
    FollowedAuthorListView,
    FollowedNarratorListView,
    FollowNarratorView,
    SavedPlaylistListView,
    SavePlaylistView,
)

app_name = "library"

urlpatterns = [
    path("tracks/", FavoriteTrackListView.as_view(), name="favorite-track-list"),
    path(
        "tracks/<uuid:target_id>/favorite/",
        FavoriteTrackView.as_view(),
        name="favorite-track",
    ),
    path("playlists/", SavedPlaylistListView.as_view(), name="saved-playlist-list"),
    path(
        "playlists/<uuid:target_id>/save/",
        SavePlaylistView.as_view(),
        name="save-playlist",
    ),
    path("authors/", FollowedAuthorListView.as_view(), name="followed-author-list"),
    path(
        "authors/<uuid:target_id>/follow/",
        FollowAuthorView.as_view(),
        name="follow-author",
    ),
    path(
        "narrators/",
        FollowedNarratorListView.as_view(),
        name="followed-narrator-list",
    ),
    path(
        "narrators/<uuid:target_id>/follow/",
        FollowNarratorView.as_view(),
        name="follow-narrator",
    ),
]
