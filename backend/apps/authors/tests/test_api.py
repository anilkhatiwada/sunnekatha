import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.authors.tests.factories import AuthorFactory

pytestmark = pytest.mark.django_db


def test_author_list_is_public_paginated_searchable_and_filtered():
    AuthorFactory(name_ne="पारिजात", is_featured=True, is_verified=True)
    AuthorFactory(name_ne="अर्को लेखक", is_featured=False, is_verified=True)

    response = APIClient().get(
        reverse("authors:list"),
        {"search": "पारिजात", "featured": "true", "verified": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "पारिजात"


def test_author_list_supports_ordering_and_page_size():
    AuthorFactory(name_en="Zulu")
    AuthorFactory(name_en="Alpha")

    response = APIClient().get(
        reverse("authors:list"),
        {"ordering": "name_en", "pageSize": 1},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["nameEnglish"] == "Alpha"


def test_author_list_filters_featured_and_verified_independently():
    expected = AuthorFactory(is_featured=True, is_verified=True)
    AuthorFactory(is_featured=True, is_verified=False)
    AuthorFactory(is_featured=False, is_verified=True)

    response = APIClient().get(
        reverse("authors:list"),
        {"featured": "true", "verified": "true"},
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(expected.id)


def test_author_detail_uses_slug():
    author = AuthorFactory(name_ne="पारिजात")

    response = APIClient().get(reverse("authors:detail", kwargs={"slug": author.slug}))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(author.id)
    assert response.data["biography"] == author.biography_ne


def test_featured_authors_excludes_non_featured():
    featured = AuthorFactory(is_featured=True)
    AuthorFactory(is_featured=False)

    response = APIClient().get(reverse("authors:featured"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(featured.id)


def test_author_list_uses_two_queries(django_assert_num_queries):
    AuthorFactory.create_batch(3)

    with django_assert_num_queries(2):
        response = APIClient().get(reverse("authors:list"))

    assert response.status_code == status.HTTP_200_OK
