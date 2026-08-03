import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import (
    Album,
    AudioProcessingJob,
    AudioProcessingJobStatus,
    AudioTrack,
    CopyrightStatus,
    LiteraryWork,
    TrackProcessingStatus,
)
from apps.narrators.tests.factories import NarratorFactory
from apps.taxonomy.models import ContentCategory
from apps.taxonomy.tests.factories import LanguageFactory

CATEGORY_NAMES = {
    "poem": ("कविता", "Poetry"),
    "story": ("कथा", "Story"),
    "essay": ("निबन्ध", "Essay"),
    "novel_chapter": ("उपन्यास", "Novel"),
    "folk_tale": ("लोककथा", "Folk tale"),
    "drama": ("नाटक", "Drama"),
}


def category_for_slug(slug):
    name_ne, name_en = CATEGORY_NAMES.get(slug, (slug, slug))
    category, _ = ContentCategory.objects.get_or_create(
        slug=slug,
        defaults={"name_ne": name_ne, "name_en": name_en},
    )
    return category


class LiteraryWorkFactory(DjangoModelFactory):
    class Meta:
        model = LiteraryWork
        skip_postgeneration_save = True

    title_ne = factory.Sequence(lambda number: f"साहित्यिक रचना {number}")
    title_en = factory.Sequence(lambda number: f"Literary Work {number}")
    category = factory.LazyFunction(lambda: category_for_slug("story"))
    author = factory.SubFactory(AuthorFactory)
    language = factory.SubFactory(LanguageFactory, slug="ne")
    is_published = True
    published_at = factory.LazyFunction(timezone.now)
    copyright_status = CopyrightStatus.PUBLIC_DOMAIN

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        legacy_slug = kwargs.pop("content_type", None)
        if legacy_slug:
            kwargs["category"] = category_for_slug(legacy_slug)
        return super()._adjust_kwargs(**kwargs)

    @factory.post_generation
    def genres(self, create, extracted, **kwargs):
        del kwargs
        if create and extracted:
            self.genres.add(*extracted)

    @factory.post_generation
    def moods(self, create, extracted, **kwargs):
        del kwargs
        if create and extracted:
            self.moods.add(*extracted)


class AlbumFactory(DjangoModelFactory):
    class Meta:
        model = Album
        skip_postgeneration_save = True

    title_ne = factory.Sequence(lambda number: f"एल्बम {number}")
    title_en = factory.Sequence(lambda number: f"Album {number}")
    author = factory.SubFactory(AuthorFactory)
    is_published = True

    @factory.post_generation
    def genres(self, create, extracted, **kwargs):
        del kwargs
        if create and extracted:
            self.genres.add(*extracted)

    @factory.post_generation
    def moods(self, create, extracted, **kwargs):
        del kwargs
        if create and extracted:
            self.moods.add(*extracted)


class AudioTrackFactory(DjangoModelFactory):
    class Meta:
        model = AudioTrack

    title_ne = factory.Sequence(lambda number: f"श्रव्य रचना {number}")
    title_en = factory.Sequence(lambda number: f"Audio Track {number}")
    work = factory.SubFactory(LiteraryWorkFactory)
    narrator = factory.SubFactory(NarratorFactory)
    language = factory.SubFactory(LanguageFactory, slug="ne")
    duration_seconds = 600
    processing_status = TrackProcessingStatus.READY
    is_published = True
    published_at = factory.LazyFunction(timezone.now)


class AudioProcessingJobFactory(DjangoModelFactory):
    class Meta:
        model = AudioProcessingJob

    track = factory.SubFactory(
        AudioTrackFactory,
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PENDING,
    )
    status = AudioProcessingJobStatus.QUEUED
