from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.home.models import HomeSectionItem, HomeSectionType
from apps.home.tests.factories import HomeSectionFactory
from apps.library.progress import listening_progress_service

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
    assert [item["id"] for item in response.data["sections"][0]["items"]] == [
        str(first_track.id),
        str(second_track.id),
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


def test_configured_continue_listening_uses_editorial_position():
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
        before.identifier,
        "resume",
        after.identifier,
    ]


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
