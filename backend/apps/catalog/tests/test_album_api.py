import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import AlbumFactory
from apps.taxonomy.tests.factories import GenreFactory, MoodFactory

pytestmark = pytest.mark.django_db


def test_album_list_and_detail_only_return_published_content():
    visible = AlbumFactory()
    draft = AlbumFactory(is_published=False)

    list_response = APIClient().get(reverse("catalog:album-list"))
    detail_response = APIClient().get(
        reverse("catalog:album-detail", kwargs={"slug": draft.slug})
    )

    assert list_response.data["count"] == 1
    assert list_response.data["results"][0]["id"] == str(visible.id)
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


def test_album_filters_relations_and_flags():
    author = AuthorFactory()
    genre = GenreFactory(slug="poetry")
    mood = MoodFactory(slug="calm")
    expected = AlbumFactory(
        author=author,
        genres=[genre],
        moods=[mood],
        is_featured=True,
    )
    AlbumFactory()

    response = APIClient().get(
        reverse("catalog:album-list"),
        {
            "author": author.slug,
            "genre": genre.slug,
            "mood": mood.slug,
            "featured": "true",
            "published": "true",
        },
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(expected.id)


def test_album_featured_endpoint_only_returns_featured():
    featured = AlbumFactory(is_featured=True)
    AlbumFactory(is_featured=False)

    response = APIClient().get(reverse("catalog:album-featured"))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(featured.id)


def test_album_title_search_and_ordering():
    AlbumFactory(title_en="Zebra Collection", release_date="2020-01-01")
    expected = AlbumFactory(title_en="Moon Collection", release_date="2024-01-01")

    search_response = APIClient().get(
        reverse("catalog:album-list"),
        {"search": "Moon"},
    )
    ordering_response = APIClient().get(
        reverse("catalog:album-list"),
        {"ordering": "-release_date"},
    )

    assert search_response.data["results"][0]["id"] == str(expected.id)
    assert str(ordering_response.data["results"][0]["releaseDate"]) == "2024-01-01"


def test_album_list_uses_bounded_queries(django_assert_num_queries):
    AlbumFactory.create_batch(3)

    with django_assert_num_queries(4):
        response = APIClient().get(reverse("catalog:album-list"))

    assert response.status_code == status.HTTP_200_OK
