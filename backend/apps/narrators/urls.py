from django.urls import path

from apps.narrators.views import (
    FeaturedNarratorListView,
    NarratorDetailView,
    NarratorListView,
)

app_name = "narrators"

urlpatterns = [
    path("", NarratorListView.as_view(), name="list"),
    path("featured/", FeaturedNarratorListView.as_view(), name="featured"),
    path("<str:slug>/", NarratorDetailView.as_view(), name="detail"),
]
