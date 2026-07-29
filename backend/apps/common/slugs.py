"""Unicode-safe slug generation utilities."""

import unicodedata

from django.core.exceptions import FieldDoesNotExist


def generate_unique_slug(
    instance,
    value: str,
    *,
    slug_field: str = "slug",
    queryset=None,
    fallback: str = "item",
) -> str:
    """Build a unique slug, excluding the instance itself during updates.

    A database unique constraint remains required to protect concurrent writes.
    """

    base_slug = _unicode_slugify(value) or fallback
    max_length = _get_slug_max_length(instance, slug_field)
    queryset = (
        queryset if queryset is not None else type(instance)._default_manager.all()
    )

    instance_pk = getattr(instance, "pk", None)
    if instance_pk:
        queryset = queryset.exclude(pk=instance_pk)

    candidate = base_slug[:max_length].rstrip("-")
    suffix = 2
    while queryset.filter(**{slug_field: candidate}).exists():
        marker = f"-{suffix}"
        candidate = f"{base_slug[: max_length - len(marker)].rstrip('-')}{marker}"
        suffix += 1

    return candidate


def _unicode_slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).casefold()
    characters = []
    previous_was_separator = False

    for character in normalized:
        category = unicodedata.category(character)
        if category[0] in {"L", "M", "N"}:
            characters.append(character)
            previous_was_separator = False
        elif character.isspace() or character in {"-", "_"}:
            if characters and not previous_was_separator:
                characters.append("-")
                previous_was_separator = True

    return "".join(characters).strip("-")


def _get_slug_max_length(instance, slug_field: str) -> int:
    try:
        field = instance._meta.get_field(slug_field)
    except FieldDoesNotExist:
        return 255
    return field.max_length or 255
