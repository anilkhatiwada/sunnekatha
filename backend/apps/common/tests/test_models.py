import uuid
from types import SimpleNamespace

from django.db import models
from django.utils import timezone

from apps.common.models import (
    PublicationStatus,
    SoftPublishableModel,
    UUIDTimeStampedModel,
)


def test_uuid_timestamped_model_is_abstract():
    assert UUIDTimeStampedModel._meta.abstract is True
    assert isinstance(UUIDTimeStampedModel._meta.get_field("id"), models.UUIDField)
    assert UUIDTimeStampedModel._meta.get_field("id").primary_key is True
    assert UUIDTimeStampedModel._meta.get_field("id").default is uuid.uuid4


def test_soft_publishable_model_is_abstract():
    assert SoftPublishableModel._meta.abstract is True


def test_soft_publication_lifecycle():
    item = SimpleNamespace(
        publication_status=PublicationStatus.DRAFT,
        published_at=None,
    )
    published_at = timezone.now()

    SoftPublishableModel.publish(item, at=published_at)
    assert item.publication_status == PublicationStatus.PUBLISHED
    assert item.published_at == published_at
    assert SoftPublishableModel.is_published.fget(item) is True

    SoftPublishableModel.archive(item)
    assert item.publication_status == PublicationStatus.ARCHIVED
    assert SoftPublishableModel.is_published.fget(item) is False

    SoftPublishableModel.unpublish(item)
    assert item.publication_status == PublicationStatus.DRAFT
    assert item.published_at is None
