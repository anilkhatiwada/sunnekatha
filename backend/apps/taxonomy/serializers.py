from rest_framework import serializers

from apps.taxonomy.models import ContentCategory, Genre, Language, Mood, Tag


class TaxonomySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_ne")
    nameEnglish = serializers.CharField(source="name_en")
    sortOrder = serializers.IntegerField(source="sort_order")
    isActive = serializers.BooleanField(source="is_active")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        fields = (
            "id",
            "slug",
            "name",
            "nameEnglish",
            "description",
            "image",
            "sortOrder",
            "isActive",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields


class GenreSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Genre


class MoodSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Mood


class LanguageSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Language


class ContentCategorySerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = ContentCategory


class TagSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Tag
