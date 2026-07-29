"""Ordering input normalization with an explicit field allow-list."""


def normalize_ordering(
    requested: str | None,
    *,
    allowed_fields,
    default=("-created_at",),
) -> tuple[str, ...]:
    if not requested:
        return tuple(default)

    allowed = set(allowed_fields)
    ordering = []
    for raw_field in requested.split(","):
        field = raw_field.strip()
        field_name = field.removeprefix("-")
        if field_name in allowed and field not in ordering:
            ordering.append(field)

    return tuple(ordering) or tuple(default)
