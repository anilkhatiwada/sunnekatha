import uuid

import pytest

from apps.taxonomy.models import ContentCategory, Genre, Language, Mood
from apps.taxonomy.tests.factories import GenreFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("model", [Genre, Mood, Language, ContentCategory])
def test_taxonomy_models_use_uuid_primary_keys(model):
    field = model._meta.get_field("id")

    assert field.primary_key is True
    assert field.default is uuid.uuid4


def test_taxonomy_generates_stable_unicode_slug():
    genre = GenreFactory(name_ne="जीवन र दर्शन")

    assert genre.slug == "जीवन-र-दर्शन"

    genre.name_ne = "दर्शन"
    genre.save()
    assert genre.slug == "जीवन-र-दर्शन"


def test_taxonomy_slug_collision_gets_suffix():
    GenreFactory(name_ne="कविता")

    duplicate = GenreFactory(name_ne="कविता")

    assert duplicate.slug == "कविता-2"


def test_taxonomy_default_order_uses_sort_order():
    later = GenreFactory(sort_order=20)
    earlier = GenreFactory(sort_order=10)

    assert list(Genre.objects.values_list("id", flat=True)) == [
        earlier.id,
        later.id,
    ]
