from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.authors.tests.factories import AuthorFactory

pytestmark = pytest.mark.django_db


def test_author_generates_unicode_slug_and_keeps_it_stable():
    author = AuthorFactory(name_ne="पारिजात")

    assert author.slug == "पारिजात"

    author.name_ne = "विष्णु कुमारी वाइबा"
    author.save()
    assert author.slug == "पारिजात"


def test_author_slug_collision_gets_suffix():
    AuthorFactory(name_ne="पारिजात")

    author = AuthorFactory(name_ne="पारिजात")

    assert author.slug == "पारिजात-2"


def test_author_rejects_death_before_birth():
    author = AuthorFactory.build(
        birth_date=date(1980, 1, 1),
        death_date=date(1970, 1, 1),
    )

    with pytest.raises(ValidationError) as exc_info:
        author.full_clean()

    assert "death_date" in exc_info.value.message_dict
