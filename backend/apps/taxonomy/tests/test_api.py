import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.taxonomy.tests.factories import (
    ContentCategoryFactory,
    GenreFactory,
    LanguageFactory,
    MoodFactory,
)

pytestmark = pytest.mark.django_db

ENDPOINTS = (
    ("taxonomy:genre-list", GenreFactory),
    ("taxonomy:mood-list", MoodFactory),
    ("taxonomy:language-list", LanguageFactory),
    ("taxonomy:content-category-list", ContentCategoryFactory),
)


@pytest.mark.parametrize(("url_name", "factory"), ENDPOINTS)
def test_taxonomy_lists_are_public_unpaginated_and_ordered(url_name, factory):
    later = factory(sort_order=20)
    earlier = factory(sort_order=10)

    response = APIClient().get(reverse(url_name))

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, list)
    assert [item["id"] for item in response.data] == [
        str(earlier.id),
        str(later.id),
    ]
    assert response.data[0]["name"] == earlier.name_ne
    assert response.data[0]["nameEnglish"] == earlier.name_en


@pytest.mark.parametrize(("url_name", "factory"), ENDPOINTS)
def test_taxonomy_lists_filter_active_items(url_name, factory):
    active = factory(is_active=True)
    factory(is_active=False)

    response = APIClient().get(reverse(url_name), {"active": "true"})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(active.id)


def test_taxonomy_list_supports_search_and_ordering():
    GenreFactory(name_ne="कविता", name_en="Poetry", sort_order=20)
    expected = GenreFactory(name_ne="कथा", name_en="Story", sort_order=10)

    search_response = APIClient().get(
        reverse("taxonomy:genre-list"),
        {"search": "Story"},
    )
    ordering_response = APIClient().get(
        reverse("taxonomy:genre-list"),
        {"ordering": "-sort_order"},
    )

    assert search_response.data[0]["id"] == str(expected.id)
    assert ordering_response.data[0]["sortOrder"] == 20
