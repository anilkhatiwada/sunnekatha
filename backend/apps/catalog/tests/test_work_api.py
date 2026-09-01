from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import WorkStructure
from apps.catalog.tests.factories import AudioTrackFactory, LiteraryWorkFactory
from apps.taxonomy.tests.factories import (
    ContentCategoryFactory,
    GenreFactory,
    LanguageFactory,
    MoodFactory,
    TagFactory,
)

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

    # Pagination + works + four bounded M2M prefetches (genres, moods,
    # categories, tags), independent of result count.
    with django_assert_num_queries(6):
        response = APIClient().get(reverse("catalog:work-list"))

    assert response.status_code == status.HTTP_200_OK


def test_serialized_work_returns_ordered_chapters_categories_and_tags():
    extra_category = ContentCategoryFactory(slug="romance")
    tag = TagFactory(slug="family")
    work = LiteraryWorkFactory(
        structure=WorkStructure.SERIALIZED,
        categories=[extra_category],
        tags=[tag],
    )
    second = AudioTrackFactory(work=work, chapter_number=2, track_number=2)
    first = AudioTrackFactory(work=work, chapter_number=1, track_number=1)

    response = APIClient().get(
        reverse("catalog:work-detail", kwargs={"slug": work.slug})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["structure"] == "serialized"
    assert [item["id"] for item in response.data["chapters"]] == [
        str(first.id),
        str(second.id),
    ]
    assert {item["slug"] for item in response.data["categories"]} == {
        work.category.slug,
        "romance",
    }
    assert [item["slug"] for item in response.data["tags"]] == ["family"]


def test_catalog_items_replace_serialized_chapters_with_parent_work():
    standalone = AudioTrackFactory()
    work = LiteraryWorkFactory(structure=WorkStructure.SERIALIZED)
    AudioTrackFactory(work=work, chapter_number=1)
    AudioTrackFactory(work=work, chapter_number=2)

    response = APIClient().get(reverse("catalog:catalog-item-list"))

    assert response.status_code == status.HTTP_200_OK
    identities = {
        (item["kind"], item["content"]["id"]) for item in response.data["results"]
    }
    assert ("track", str(standalone.id)) in identities
    assert ("work", str(work.id)) in identities
    assert not any(
        kind == "track" and identity != str(standalone.id)
        for kind, identity in identities
    )
