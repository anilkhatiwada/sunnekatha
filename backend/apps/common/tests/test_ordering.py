from apps.common.ordering import normalize_ordering


def test_ordering_keeps_only_allowed_unique_fields():
    assert normalize_ordering(
        "-published_at,title,-secret,title",
        allowed_fields={"published_at", "title"},
    ) == ("-published_at", "title")


def test_ordering_uses_default_when_input_is_invalid():
    assert normalize_ordering(
        "private_field",
        allowed_fields={"title"},
        default=("title",),
    ) == ("title",)
