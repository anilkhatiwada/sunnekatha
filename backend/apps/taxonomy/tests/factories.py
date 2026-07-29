import factory
from factory.django import DjangoModelFactory

from apps.taxonomy.models import ContentCategory, Genre, Language, Mood


class TaxonomyFactory(DjangoModelFactory):
    name_ne = factory.Sequence(lambda number: f"वर्ग {number}")
    name_en = factory.Sequence(lambda number: f"Taxonomy {number}")
    description = "परीक्षण विवरण"

    class Meta:
        abstract = True


class GenreFactory(TaxonomyFactory):
    class Meta:
        model = Genre


class MoodFactory(TaxonomyFactory):
    class Meta:
        model = Mood


class LanguageFactory(TaxonomyFactory):
    slug = factory.Sequence(lambda number: f"language-{number}")

    class Meta:
        model = Language
        django_get_or_create = ("slug",)


class ContentCategoryFactory(TaxonomyFactory):
    class Meta:
        model = ContentCategory
