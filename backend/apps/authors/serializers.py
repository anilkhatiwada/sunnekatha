from rest_framework import serializers

from apps.authors.models import Author


class CompactAuthorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_ne")
    nameEnglish = serializers.CharField(source="name_en")
    isFeatured = serializers.BooleanField(source="is_featured")
    isVerified = serializers.BooleanField(source="is_verified")

    class Meta:
        model = Author
        fields = (
            "id",
            "slug",
            "name",
            "nameEnglish",
            "image",
            "isFeatured",
            "isVerified",
        )
        read_only_fields = fields


class AuthorSerializer(CompactAuthorSerializer):
    biography = serializers.CharField(source="biography_ne")
    biographyEnglish = serializers.CharField(source="biography_en")
    birthDate = serializers.DateField(source="birth_date")
    deathDate = serializers.DateField(source="death_date")
    birthYear = serializers.SerializerMethodField()
    deathYear = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta(CompactAuthorSerializer.Meta):
        fields = CompactAuthorSerializer.Meta.fields + (
            "biography",
            "biographyEnglish",
            "birthDate",
            "deathDate",
            "birthYear",
            "deathYear",
            "country",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields

    def get_birthYear(self, obj: Author) -> int | None:
        return obj.birth_date.year if obj.birth_date else None

    def get_deathYear(self, obj: Author) -> int | None:
        return obj.death_date.year if obj.death_date else None
