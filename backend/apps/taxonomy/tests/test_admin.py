import pytest
from django.contrib import admin

from apps.taxonomy.admin import TaxonomyAdmin
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood


@pytest.mark.parametrize("model", [Genre, Mood, Language, ContentCategory])
def test_taxonomy_models_are_registered_with_shared_admin(model):
    assert isinstance(admin.site._registry[model], TaxonomyAdmin)
