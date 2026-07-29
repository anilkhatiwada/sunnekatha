import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.narrators.tests.factories import NarratorFactory

pytestmark = pytest.mark.django_db


def test_narrator_list_is_public_paginated_searchable_and_filtered():
    NarratorFactory(
        name_ne="आशा",
        is_featured=True,
        is_verified=True,
    )
    NarratorFactory(
        name_ne="अर्को वाचक",
        is_featured=False,
        is_verified=True,
    )

    response = APIClient().get(
        reverse("narrators:list"),
        {"search": "आशा", "featured": "true", "verified": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "आशा"


def test_narrator_list_orders_by_follower_count():
    NarratorFactory(name_en="Low", follower_count_cache=2)
    NarratorFactory(name_en="High", follower_count_cache=50)

    response = APIClient().get(
        reverse("narrators:list"),
        {"ordering": "-follower_count_cache"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["followerCount"] == 50


def test_narrator_list_filters_featured_and_verified_independently():
    expected = NarratorFactory(is_featured=True, is_verified=True)
    NarratorFactory(is_featured=True, is_verified=False)
    NarratorFactory(is_featured=False, is_verified=True)

    response = APIClient().get(
        reverse("narrators:list"),
        {"featured": "true", "verified": "true"},
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(expected.id)


def test_narrator_detail_uses_slug_and_safe_linked_user_summary():
    user = UserFactory()
    narrator = NarratorFactory(user=user)

    response = APIClient().get(
        reverse("narrators:detail", kwargs={"slug": narrator.slug})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["linkedUser"]["id"] == str(user.id)
    assert response.data["linkedUser"]["displayName"] == user.display_name
    assert "email" not in response.data["linkedUser"]


def test_narrator_without_user_serializes_null_link():
    narrator = NarratorFactory(user=None)

    response = APIClient().get(
        reverse("narrators:detail", kwargs={"slug": narrator.slug})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["linkedUser"] is None


def test_featured_narrators_excludes_non_featured():
    featured = NarratorFactory(is_featured=True)
    NarratorFactory(is_featured=False)

    response = APIClient().get(reverse("narrators:featured"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(featured.id)


def test_narrator_list_avoids_linked_user_n_plus_one(django_assert_num_queries):
    users = UserFactory.create_batch(3)
    for user in users:
        NarratorFactory(user=user)

    with django_assert_num_queries(2):
        response = APIClient().get(reverse("narrators:list"))

    assert response.status_code == status.HTTP_200_OK
