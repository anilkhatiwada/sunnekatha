from io import StringIO

import pytest
from django.core.management import call_command

from apps.taxonomy.management.commands.seed_taxonomies import SEED_GROUPS
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood

pytestmark = pytest.mark.django_db


def test_seed_taxonomies_creates_expected_common_values():
    output = StringIO()

    call_command("seed_taxonomies", stdout=output)

    seeded_names = set()
    for model in (Genre, Mood, ContentCategory):
        seeded_names.update(model.objects.values_list("name_ne", flat=True))

    assert {
        "कविता",
        "कथा",
        "निबन्ध",
        "उपन्यास",
        "लोककथा",
        "नाटक",
        "प्रेम",
        "दर्शन",
        "प्रेरणा",
        "बालसाहित्य",
        "वर्षा",
        "शान्ति",
        "विरह",
    }.issubset(seeded_names)
    assert Language.objects.filter(slug="ne", name_ne="नेपाली").exists()
    assert "created" in output.getvalue()


def test_seed_taxonomies_is_idempotent_and_updates_managed_fields():
    call_command("seed_taxonomies", stdout=StringIO())
    expected_count = sum(len(records) for _, records in SEED_GROUPS)
    Genre.objects.filter(slug="poetry").update(name_ne="Changed")
    output = StringIO()

    call_command("seed_taxonomies", stdout=output)

    actual_count = sum(model.objects.count() for model, _ in SEED_GROUPS)
    assert actual_count == expected_count
    assert Genre.objects.get(slug="poetry").name_ne == "कविता"
    assert f"{expected_count} updated" in output.getvalue()
