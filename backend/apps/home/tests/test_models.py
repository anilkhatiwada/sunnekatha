from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.tests.factories import AlbumFactory, AudioTrackFactory
from apps.home.models import (
    HomeSection,
    HomeSectionItem,
    HomeSectionSource,
    HomeSectionType,
)
from apps.home.tests.factories import HomeSectionFactory
from apps.playlists.tests.factories import PlaylistFactory
from apps.taxonomy.tests.factories import ContentCategoryFactory

pytestmark = pytest.mark.django_db


def test_active_sections_respect_status_and_schedule():
    now = timezone.now()
    visible = HomeSectionFactory(starts_at=now - timedelta(hours=1))
    HomeSectionFactory(is_active=False)
    HomeSectionFactory(starts_at=now + timedelta(hours=1))
    HomeSectionFactory(ends_at=now)

    assert list(HomeSection.objects.active(at=now)) == [visible]


def test_section_rejects_invalid_schedule():
    section = HomeSectionFactory.build(
        starts_at=timezone.now(),
        ends_at=timezone.now() - timedelta(minutes=1),
    )
    with pytest.raises(ValidationError, match="End time"):
        section.full_clean()


def test_item_requires_exactly_one_target():
    section = HomeSectionFactory(section_type=HomeSectionType.TRACKS)
    item = HomeSectionItem(section=section, position=1)
    with pytest.raises(ValidationError, match="exactly one"):
        item.full_clean()

    item.track = AudioTrackFactory()
    item.album = AlbumFactory()
    with pytest.raises(ValidationError, match="exactly one"):
        item.full_clean()


def test_item_target_must_match_section_type():
    section = HomeSectionFactory(section_type=HomeSectionType.PLAYLISTS)
    item = HomeSectionItem(
        section=section,
        track=AudioTrackFactory(),
        position=1,
    )
    with pytest.raises(ValidationError, match="not valid"):
        item.full_clean()


def test_section_rejects_type_change_incompatible_with_existing_items():
    section = HomeSectionFactory(section_type=HomeSectionType.TRACKS)
    HomeSectionItem.objects.create(
        section=section,
        track=AudioTrackFactory(),
        position=1,
    )
    section.section_type = HomeSectionType.PLAYLISTS

    with pytest.raises(ValidationError, match="Existing items"):
        section.full_clean()


def test_hero_accepts_track_playlist_or_album():
    section = HomeSectionFactory(section_type=HomeSectionType.HERO)
    for field, target in (
        ("track", AudioTrackFactory()),
        ("playlist", PlaylistFactory()),
        ("album", AlbumFactory()),
    ):
        item = HomeSectionItem(section=section, position=1, **{field: target})
        item.full_clean()


def test_category_section_accepts_one_active_category():
    section = HomeSectionFactory(section_type=HomeSectionType.CATEGORIES)
    item = HomeSectionItem(
        section=section,
        category=ContentCategoryFactory(),
        position=1,
    )

    item.full_clean()


def test_automatic_source_and_browse_category_require_track_sections():
    invalid_source = HomeSectionFactory.build(
        section_type=HomeSectionType.AUTHORS,
        content_source=HomeSectionSource.RECENT_RELEASES,
    )
    with pytest.raises(ValidationError, match="new releases"):
        invalid_source.full_clean()

    invalid_category = HomeSectionFactory.build(
        section_type=HomeSectionType.AUTHORS,
        browse_category=ContentCategoryFactory(),
    )
    with pytest.raises(ValidationError, match="browse category"):
        invalid_category.full_clean()


def test_database_rejects_multiple_targets_and_duplicate_positions():
    section = HomeSectionFactory(section_type=HomeSectionType.HERO)
    track = AudioTrackFactory()
    playlist = PlaylistFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        HomeSectionItem.objects.create(
            section=section,
            track=track,
            playlist=playlist,
            position=1,
        )

    HomeSectionItem.objects.create(section=section, track=track, position=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        HomeSectionItem.objects.create(
            section=section,
            playlist=playlist,
            position=1,
        )
