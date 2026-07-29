import factory

from apps.analytics.models import (
    DailyAuthorMetric,
    DailyNarratorMetric,
    DailyPlatformMetric,
    DailyPlaylistMetric,
    DailyTrackMetric,
)


class DailyMetricFactoryBase(factory.django.DjangoModelFactory):
    date = factory.Faker("date_object")
    total_plays = 10
    unique_listeners = 3
    listening_seconds = 3600
    completed_plays = 5

    class Meta:
        abstract = True


class DailyPlatformMetricFactory(DailyMetricFactoryBase):
    class Meta:
        model = DailyPlatformMetric


class DailyTrackMetricFactory(DailyMetricFactoryBase):
    class Meta:
        model = DailyTrackMetric

    track = factory.SubFactory("apps.catalog.tests.factories.AudioTrackFactory")


class DailyAuthorMetricFactory(DailyMetricFactoryBase):
    class Meta:
        model = DailyAuthorMetric

    author = factory.SubFactory("apps.authors.tests.factories.AuthorFactory")


class DailyNarratorMetricFactory(DailyMetricFactoryBase):
    class Meta:
        model = DailyNarratorMetric

    narrator = factory.SubFactory("apps.narrators.tests.factories.NarratorFactory")


class DailyPlaylistMetricFactory(DailyMetricFactoryBase):
    class Meta:
        model = DailyPlaylistMetric

    playlist = factory.SubFactory("apps.playlists.tests.factories.PlaylistFactory")
