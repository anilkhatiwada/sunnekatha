from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.home.models import HomeSectionItem, HomeSectionSource, HomeSectionType
from apps.home.tests.factories import HomeSectionFactory
from apps.library.progress import listening_progress_service
from apps.taxonomy.tests.factories import ContentCategoryFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_active_editorial_sections_control_order_titles_and_items():
    first_track = AudioTrackFactory(title_ne="पहिलो")
    second_track = AudioTrackFactory(title_ne="दोस्रो")
    second_section = HomeSectionFactory(
        identifier="editors-picks",
        title_ne="सम्पादकको रोजाइ",
        section_type=HomeSectionType.TRACKS,
        sort_order=20,
    )
    first_section = HomeSectionFactory(
        identifier="new-poems",
        title_ne="नयाँ कविता",
        section_type=HomeSectionType.TRACKS,
        sort_order=10,
        subtitle_ne="आजका उत्कृष्ट रचना",
        layout="grid",
        max_items=1,
    )
    HomeSectionItem.objects.create(
        section=first_section, track=second_track, position=2
    )
    HomeSectionItem.objects.create(section=first_section, track=first_track, position=1)
    HomeSectionItem.objects.create(
        section=second_section, track=second_track, position=1
    )

    response = APIClient().get(reverse("home:detail"))

    assert [item["id"] for item in response.data["sections"]] == [
        "new-poems",
        "editors-picks",
    ]
    assert response.data["sections"][0]["title"] == "नयाँ कविता"
    assert response.data["sections"][0]["subtitle"] == "आजका उत्कृष्ट रचना"
    assert response.data["sections"][0]["sectionType"] == "tracks"
    assert response.data["sections"][0]["layout"] == "grid"
    assert [item["id"] for item in response.data["sections"][0]["items"]] == [
        str(first_track.id),
    ]


def test_inactive_scheduled_and_unpublished_editorial_content_is_hidden():
    visible = AudioTrackFactory()
    hidden = AudioTrackFactory(is_published=False, published_at=None)
    section = HomeSectionFactory(section_type=HomeSectionType.TRACKS)
    inactive = HomeSectionFactory(
        section_type=HomeSectionType.ALBUMS,
        is_active=False,
    )
    future = HomeSectionFactory(
        section_type=HomeSectionType.ALBUMS,
        starts_at=timezone.now() + timedelta(days=1),
    )
    expired = HomeSectionFactory(
        section_type=HomeSectionType.ALBUMS,
        ends_at=timezone.now() - timedelta(seconds=1),
    )
    HomeSectionItem.objects.create(section=section, track=visible, position=1)
    HomeSectionItem.objects.create(section=section, track=hidden, position=2)
    HomeSectionItem.objects.create(section=inactive, album=AlbumFactory(), position=1)
    HomeSectionItem.objects.create(section=future, album=AlbumFactory(), position=1)
    HomeSectionItem.objects.create(section=expired, album=AlbumFactory(), position=1)

    response = APIClient().get(reverse("home:detail"))

    assert [value["id"] for value in response.data["sections"]] == [section.identifier]
    assert [item["id"] for item in response.data["sections"][0]["items"]] == [
        str(visible.id)
    ]


def test_editorial_hero_uses_first_visible_item():
    hero = HomeSectionFactory(
        identifier="featured-story",
        title_ne="आजको विशेष",
        section_type=HomeSectionType.HERO,
    )
    album = AlbumFactory()
    HomeSectionItem.objects.create(section=hero, album=album, position=1)

    response = APIClient().get(reverse("home:detail"))

    assert response.data["hero"]["id"] == "featured-story"
    assert response.data["hero"]["contentType"] == "album"
    assert response.data["hero"]["content"]["id"] == str(album.id)


def test_newest_featured_track_takes_priority_over_editorial_hero():
    hero = HomeSectionFactory(
        identifier="featured-story",
        section_type=HomeSectionType.HERO,
    )
    HomeSectionItem.objects.create(section=hero, album=AlbumFactory(), position=1)
    older = AudioTrackFactory(
        is_featured=True,
        published_at=timezone.now() - timedelta(days=2),
    )
    newest = AudioTrackFactory(
        is_featured=True,
        published_at=timezone.now() - timedelta(hours=1),
    )
    AudioTrackFactory(
        is_featured=False,
        published_at=timezone.now(),
    )

    response = APIClient().get(reverse("home:detail"))

    assert response.data["hero"]["id"] == "latest-featured-track"
    assert response.data["hero"]["contentType"] == "track"
    assert response.data["hero"]["content"]["id"] == str(newest.id)
    assert response.data["hero"]["content"]["id"] != str(older.id)


def test_configured_continue_listening_is_always_immediately_after_hero():
    before = HomeSectionFactory(
        section_type=HomeSectionType.ALBUMS,
        sort_order=10,
    )
    HomeSectionItem.objects.create(section=before, album=AlbumFactory(), position=1)
    HomeSectionFactory(
        identifier="resume",
        title_ne="सुन्न जारी राख्नुहोस्",
        section_type=HomeSectionType.CONTINUE_LISTENING,
        sort_order=20,
    )
    after = HomeSectionFactory(
        section_type=HomeSectionType.TRACKS,
        sort_order=30,
    )
    HomeSectionItem.objects.create(section=after, track=AudioTrackFactory(), position=1)
    user = UserFactory()
    progress_track = AudioTrackFactory(duration_seconds=100)
    listening_progress_service.update(
        user=user,
        track=progress_track,
        position_seconds=20,
        duration_seconds=100,
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(reverse("home:detail"))

    assert [section["id"] for section in response.data["sections"]] == [
        "resume",
        before.identifier,
        after.identifier,
    ]


def test_automatic_new_releases_ignores_editorial_items_and_uses_publish_order():
    older = AudioTrackFactory(published_at=timezone.now() - timedelta(days=2))
    newer = AudioTrackFactory(published_at=timezone.now() - timedelta(hours=1))
    section = HomeSectionFactory(
        identifier="new-releases",
        section_type=HomeSectionType.TRACKS,
        content_source=HomeSectionSource.RECENT_RELEASES,
        max_items=1,
    )
    HomeSectionItem.objects.create(section=section, track=older, position=1)

    response = APIClient().get(reverse("home:detail"))

    assert [item["id"] for item in response.data["sections"][0]["items"]] == [
        str(newer.id)
    ]


def test_track_section_exposes_structured_browse_category():
    category = ContentCategoryFactory(name_ne="कविता")
    section = HomeSectionFactory(
        section_type=HomeSectionType.TRACKS,
        browse_category=category,
    )
    HomeSectionItem.objects.create(
        section=section, track=AudioTrackFactory(), position=1
    )

    response = APIClient().get(reverse("home:detail"))

    assert response.data["sections"][0]["browseCategory"] == {
        "slug": category.slug,
        "name": "कविता",
    }


def test_editing_section_invalidates_public_cache():
    section = HomeSectionFactory(
        title_ne="पुरानो शीर्षक",
        section_type=HomeSectionType.TRACKS,
    )
    HomeSectionItem.objects.create(
        section=section, track=AudioTrackFactory(), position=1
    )
    first = APIClient().get(reverse("home:detail"))
    assert first.data["sections"][0]["title"] == "पुरानो शीर्षक"

    section.title_ne = "नयाँ शीर्षक"
    section.save(update_fields=("title_ne", "updated_at"))
    second = APIClient().get(reverse("home:detail"))
    assert second.data["sections"][0]["title"] == "नयाँ शीर्षक"


def test_editorial_category_section_returns_up_to_six_active_categories():
    section = HomeSectionFactory(
        identifier="browse-categories",
        title_ne="विधाअनुसार अन्वेषण",
        section_type=HomeSectionType.CATEGORIES,
        layout="grid",
        max_items=12,
    )
    categories = [
        ContentCategoryFactory(
            name_ne=f"विधा {index}",
            name_en=f"Category {index}",
            sort_order=index,
            is_active=True,
        )
        for index in range(7)
    ]
    inactive = ContentCategoryFactory(is_active=False)
    HomeSectionItem.objects.create(section=section, category=inactive, position=1)

    response = APIClient().get(reverse("home:detail"))

    assert response.status_code == 200
    payload = response.data["sections"][0]
    assert payload["sectionType"] == "categories"
    assert payload["layout"] == "grid"
    assert [item["id"] for item in payload["items"]] == [
        str(category.id) for category in categories[:6]
    ]
    assert str(inactive.id) not in {item["id"] for item in payload["items"]}
