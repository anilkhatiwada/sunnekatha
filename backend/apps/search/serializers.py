from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        max_length=200,
    )
    type = serializers.ChoiceField(
        choices=(
            "all",
            "tracks",
            "works",
            "playlists",
            "albums",
            "authors",
            "narrators",
            "genres",
            "moods",
        ),
        required=False,
        default="all",
    )
    content_type = serializers.ChoiceField(
        choices=("poem", "story", "essay", "novel_chapter", "folk_tale", "drama"),
        required=False,
    )
    query = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        write_only=True,
    )
    resultType = serializers.ChoiceField(
        choices=(
            "all",
            "tracks",
            "works",
            "playlists",
            "albums",
            "authors",
            "narrators",
            "genres",
            "moods",
        ),
        required=False,
        write_only=True,
    )
    contentType = serializers.ChoiceField(
        choices=("poem", "story", "essay", "novel_chapter", "folk_tale", "drama"),
        required=False,
        write_only=True,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        self._apply_alias(attrs, canonical="q", alias="query")
        self._apply_alias(attrs, canonical="type", alias="resultType")
        self._apply_alias(
            attrs,
            canonical="content_type",
            alias="contentType",
        )
        return attrs

    def _apply_alias(self, attrs, *, canonical, alias):
        alias_value = attrs.pop(alias, None)
        if alias_value is None:
            return
        canonical_value = attrs.get(canonical)
        if canonical in self.initial_data and canonical_value != alias_value:
            raise serializers.ValidationError(
                {alias: f"Conflicts with the {canonical} parameter."}
            )
        attrs[canonical] = alias_value


class GroupedSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    tracks = serializers.ListField(child=serializers.JSONField())
    literaryWorks = serializers.ListField(child=serializers.JSONField())
    playlists = serializers.ListField(child=serializers.JSONField())
    albums = serializers.ListField(child=serializers.JSONField())
    authors = serializers.ListField(child=serializers.JSONField())
    narrators = serializers.ListField(child=serializers.JSONField())
    genres = serializers.ListField(child=serializers.JSONField())
    moods = serializers.ListField(child=serializers.JSONField())


class AutocompleteItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.UUIDField()
    slug = serializers.CharField()
    label = serializers.CharField()
    labelEnglish = serializers.CharField(allow_blank=True)


class TrendingSearchResponseSerializer(serializers.Serializer):
    searches = serializers.ListField(child=serializers.CharField())
