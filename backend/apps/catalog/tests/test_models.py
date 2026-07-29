from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalog.tests.factories import AlbumFactory, LiteraryWorkFactory

pytestmark = pytest.mark.django_db


def test_work_generates_stable_unicode_slug():
    work = LiteraryWorkFactory(title_ne="शिरीषको फूल")

    assert work.slug == "शिरीषको-फूल"
    work.title_ne = "Changed"
    work.save()
    assert work.slug == "शिरीषको-फूल"


def test_album_generates_unique_slug():
    AlbumFactory(title_ne="कविता सङ्ग्रह")

    duplicate = AlbumFactory(title_ne="कविता सङ्ग्रह")

    assert duplicate.slug == "कविता-सङ्ग्रह-2"


def test_published_work_requires_timestamp():
    work = LiteraryWorkFactory.build(is_published=True, published_at=None)

    with pytest.raises(ValidationError) as exc_info:
        work.full_clean()

    assert "published_at" in exc_info.value.message_dict


def test_work_rejects_future_publication_year():
    work = LiteraryWorkFactory.build(publication_year=date.today().year + 1)

    with pytest.raises(ValidationError) as exc_info:
        work.full_clean()

    assert "publication_year" in exc_info.value.message_dict


def test_published_work_queryset_excludes_drafts_and_scheduled_items():
    visible = LiteraryWorkFactory()
    LiteraryWorkFactory(is_published=False, published_at=None)
    LiteraryWorkFactory(published_at=timezone.now() + timedelta(days=1))

    assert list(LiteraryWorkFactory._meta.model.objects.published()) == [visible]


def test_published_album_queryset_excludes_drafts():
    visible = AlbumFactory()
    AlbumFactory(is_published=False)

    assert list(AlbumFactory._meta.model.objects.published()) == [visible]
