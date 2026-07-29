from django.urls import path

from apps.authors.views import (
    AuthorDetailView,
    AuthorListView,
    FeaturedAuthorListView,
)

app_name = "authors"

urlpatterns = [
    path("", AuthorListView.as_view(), name="list"),
    path("featured/", FeaturedAuthorListView.as_view(), name="featured"),
    path("<str:slug>/", AuthorDetailView.as_view(), name="detail"),
]
