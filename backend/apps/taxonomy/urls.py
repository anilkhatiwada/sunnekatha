from django.urls import path

from apps.taxonomy.views import (
    ContentCategoryListView,
    GenreListView,
    LanguageListView,
    MoodListView,
)

app_name = "taxonomy"

urlpatterns = [
    path("genres/", GenreListView.as_view(), name="genre-list"),
    path("moods/", MoodListView.as_view(), name="mood-list"),
    path("languages/", LanguageListView.as_view(), name="language-list"),
    path(
        "content-categories/",
        ContentCategoryListView.as_view(),
        name="content-category-list",
    ),
]
