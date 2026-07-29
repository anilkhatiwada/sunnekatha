from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import AudioTrack, TrackProcessingStatus
from apps.catalog.tests.factories import (
    AlbumFactory,
    AudioTrackFactory,
    LiteraryWorkFactory,
)

pytestmark = pytest.mark.django_db


def test_track_generates_slug_and_syncs_content_type():
    track = AudioTrackFactory(
        title_ne="वर्षाको साँझ",
        work__content_type="poem",
    )

    assert track.slug == "वर्षाको-साँझ"
    assert track.content_type == "poem"


def test_published_queryset_enforces_time_status_and_flag():
    visible = AudioTrackFactory()
    AudioTrackFactory(is_published=False, published_at=None)
    AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
    )
    AudioTrackFactory(published_at=timezone.now() + timedelta(days=1))

    assert list(AudioTrack.objects.published()) == [visible]


def test_track_validation_requires_ready_timestamp_for_publication():
    track = AudioTrackFactory()
    track.published_at = None
    track.processing_status = TrackProcessingStatus.PROCESSING

    with pytest.raises(ValidationError) as exc_info:
        track.full_clean(exclude={"slug"})

    assert {"published_at", "processing_status"}.issubset(exc_info.value.message_dict)


def test_track_rejects_album_from_different_author():
    work = LiteraryWorkFactory(author=AuthorFactory())
    album = AlbumFactory(author=AuthorFactory())
    track = AudioTrackFactory.build(work=work, album=album)

    with pytest.raises(ValidationError) as exc_info:
        track.full_clean()

    assert "album" in exc_info.value.message_dict


def test_track_indexed_fields_are_configured():
    assert AudioTrack._meta.get_field("slug").unique is True
    for field_name in (
        "published_at",
        "content_type",
        "is_featured",
        "is_published",
    ):
        assert AudioTrack._meta.get_field(field_name).db_index is True

    indexed_field_sets = {
        tuple(field.removeprefix("-") for field in index.fields)
        for index in AudioTrack._meta.indexes
    }
    assert ("narrator", "is_published", "published_at") in indexed_field_sets
    assert ("work", "track_number") in indexed_field_sets
    assert ("album", "track_number") in indexed_field_sets
