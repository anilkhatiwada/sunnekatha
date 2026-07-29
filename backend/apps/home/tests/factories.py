import factory

from apps.home.models import HomeSection, HomeSectionItem, HomeSectionType


class HomeSectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HomeSection

    identifier = factory.Sequence(lambda value: f"section-{value}")
    title_ne = factory.Sequence(lambda value: f"खण्ड {value}")
    title_en = factory.Sequence(lambda value: f"Section {value}")
    section_type = HomeSectionType.TRACKS
    sort_order = factory.Sequence(lambda value: value)
    is_active = True


class HomeSectionItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HomeSectionItem

    section = factory.SubFactory(HomeSectionFactory)
    track = factory.SubFactory("apps.catalog.tests.factories.AudioTrackFactory")
    position = factory.Sequence(lambda value: value)
