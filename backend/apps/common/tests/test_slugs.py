from types import SimpleNamespace
from unittest.mock import MagicMock

from apps.common.slugs import generate_unique_slug


def create_instance(*, pk=None, max_length=50):
    field = SimpleNamespace(max_length=max_length)
    meta = SimpleNamespace(get_field=lambda name: field)
    return SimpleNamespace(pk=pk, _meta=meta)


def test_slug_generation_preserves_nepali_unicode():
    queryset = MagicMock()
    queryset.filter.return_value.exists.return_value = False

    slug = generate_unique_slug(
        create_instance(),
        "वर्षाको साँझ",
        queryset=queryset,
    )

    assert slug == "वर्षाको-साँझ"


def test_slug_generation_adds_incrementing_suffix():
    queryset = MagicMock()
    queryset.filter.return_value.exists.side_effect = [True, True, False]

    slug = generate_unique_slug(
        create_instance(max_length=12),
        "Repeated title",
        queryset=queryset,
    )

    assert slug == "repeated-t-3"


def test_slug_generation_excludes_existing_instance():
    queryset = MagicMock()
    queryset.exclude.return_value = queryset
    queryset.filter.return_value.exists.return_value = False

    generate_unique_slug(
        create_instance(pk="existing"),
        "Existing",
        queryset=queryset,
    )

    queryset.exclude.assert_called_once_with(pk="existing")
