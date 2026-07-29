from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import LiteraryWorkFactory
from apps.taxonomy.tests.factories import GenreFactory, LanguageFactory, MoodFactory

pytestmark = pytest.mark.django_db


def test_work_list_only_returns_currently_published_content():
    visible = LiteraryWorkFactory()
    LiteraryWorkFactory(is_published=False, published_at=None)
    LiteraryWorkFactory(published_at=timezone.now() + timedelta(days=1))

    response = APIClient().get(reverse("catalog:work-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(visible.id)


def test_unpublished_work_detail_returns_not_found():
    draft = LiteraryWorkFactory(is_published=False, published_at=None)

    response = APIClient().get(
        reverse("catalog:work-detail", kwargs={"slug": draft.slug})
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_work_filters_all_catalog_relations_and_flags():
    author = AuthorFactory()
    language = LanguageFactory(slug="ne")
    genre = GenreFactory(slug="poetry")
    mood = MoodFactory(slug="calm")
    expected = LiteraryWorkFactory(
        content_type="poem",
        author=author,
        language=language,
        genres=[genre],
        moods=[mood],
        is_featured=True,
    )
    LiteraryWorkFactory(content_type="story")

    response = APIClient().get(
        reverse("catalog:work-list"),
        {
            "contentType": "poem",
            "author": author.slug,
            "language": language.slug,
            "genre": genre.slug,
            "mood": mood.slug,
            "featured": "true",
            "published": "true",
        },
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(expected.id)
    assert response.data["results"][0]["genres"] == ["poetry"]
    assert response.data["results"][0]["language"] == "ne"


def test_work_featured_endpoint_only_returns_featured():
    featured = LiteraryWorkFactory(is_featured=True)
    LiteraryWorkFactory(is_featured=False)

    response = APIClient().get(reverse("catalog:work-featured"))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(featured.id)


def test_work_title_search_and_ordering():
    LiteraryWorkFactory(title_en="Zebra Story", publication_year=2020)
    expected = LiteraryWorkFactory(title_en="Moon Story", publication_year=2024)

    search_response = APIClient().get(
        reverse("catalog:work-list"),
        {"search": "Moon"},
    )
    ordering_response = APIClient().get(
        reverse("catalog:work-list"),
        {"ordering": "-publication_year"},
    )

    assert search_response.data["results"][0]["id"] == str(expected.id)
    assert ordering_response.data["results"][0]["publicationYear"] == 2024


def test_work_list_uses_bounded_queries(django_assert_num_queries):
    LiteraryWorkFactory.create_batch(3)

    with django_assert_num_queries(4):
        response = APIClient().get(reverse("catalog:work-list"))

    assert response.status_code == status.HTTP_200_OK
