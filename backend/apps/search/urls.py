from django.urls import path

from apps.search.views import (
    AutocompleteView,
    GroupedSearchView,
    TrackSearchView,
    TrendingSearchView,
)

app_name = "search"

urlpatterns = [
    path("", GroupedSearchView.as_view(), name="grouped"),
    path("tracks/", TrackSearchView.as_view(), name="tracks"),
    path("autocomplete/", AutocompleteView.as_view(), name="autocomplete"),
    path("trending/", TrendingSearchView.as_view(), name="trending"),
]
