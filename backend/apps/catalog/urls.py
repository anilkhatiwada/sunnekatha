from django.urls import path

from apps.catalog.track_views import (
    FeaturedTrackListView,
    PlayerTrackView,
    RecentlyAddedTrackListView,
    RelatedTrackListView,
    TrackDetailView,
    TrackListView,
    TracksByAuthorView,
    TracksByContentTypeView,
    TracksByGenreView,
    TracksByMoodView,
    TracksByNarratorView,
    TrackStreamView,
    TrendingTrackListView,
)
from apps.catalog.views import (
    AlbumDetailView,
    AlbumListView,
    CatalogItemListView,
    FeaturedAlbumListView,
    FeaturedLiteraryWorkListView,
    LiteraryWorkDetailView,
    LiteraryWorkListView,
)

app_name = "catalog"

urlpatterns = [
    path("catalog/items/", CatalogItemListView.as_view(), name="catalog-item-list"),
    path("tracks/", TrackListView.as_view(), name="track-list"),
    path("tracks/featured/", FeaturedTrackListView.as_view(), name="track-featured"),
    path("tracks/trending/", TrendingTrackListView.as_view(), name="track-trending"),
    path("tracks/recent/", RecentlyAddedTrackListView.as_view(), name="track-recent"),
    path(
        "tracks/content-type/<str:content_type>/",
        TracksByContentTypeView.as_view(),
        name="tracks-by-content-type",
    ),
    path(
        "tracks/author/<str:slug>/",
        TracksByAuthorView.as_view(),
        name="tracks-by-author",
    ),
    path(
        "tracks/narrator/<str:slug>/",
        TracksByNarratorView.as_view(),
        name="tracks-by-narrator",
    ),
    path(
        "tracks/genre/<str:slug>/",
        TracksByGenreView.as_view(),
        name="tracks-by-genre",
    ),
    path(
        "tracks/mood/<str:slug>/",
        TracksByMoodView.as_view(),
        name="tracks-by-mood",
    ),
    path(
        "tracks/<str:slug>/related/",
        RelatedTrackListView.as_view(),
        name="track-related",
    ),
    path(
        "tracks/<str:slug>/player/",
        PlayerTrackView.as_view(),
        name="track-player",
    ),
    path(
        "tracks/<str:slug>/stream/",
        TrackStreamView.as_view(),
        name="track-stream",
    ),
    path("tracks/<str:slug>/", TrackDetailView.as_view(), name="track-detail"),
    path("works/", LiteraryWorkListView.as_view(), name="work-list"),
    path(
        "works/featured/",
        FeaturedLiteraryWorkListView.as_view(),
        name="work-featured",
    ),
    path("works/<str:slug>/", LiteraryWorkDetailView.as_view(), name="work-detail"),
    path("albums/", AlbumListView.as_view(), name="album-list"),
    path("albums/featured/", FeaturedAlbumListView.as_view(), name="album-featured"),
    path("albums/<str:slug>/", AlbumDetailView.as_view(), name="album-detail"),
]
