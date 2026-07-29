from rest_framework import serializers

from apps.narrators.models import Narrator


class LinkedNarratorUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    displayName = serializers.CharField(source="display_name")
    avatar = serializers.ImageField()


class CompactNarratorSerializer(serializers.ModelSerializer):
    linkedUser = LinkedNarratorUserSerializer(source="user")
    name = serializers.CharField(source="name_ne")
    nameEnglish = serializers.CharField(source="name_en")
    isFeatured = serializers.BooleanField(source="is_featured")
    isVerified = serializers.BooleanField(source="is_verified")
    followerCount = serializers.IntegerField(source="follower_count_cache")

    class Meta:
        model = Narrator
        fields = (
            "id",
            "slug",
            "linkedUser",
            "name",
            "nameEnglish",
            "image",
            "isFeatured",
            "isVerified",
            "followerCount",
        )
        read_only_fields = fields


class NarratorSerializer(CompactNarratorSerializer):
    biography = serializers.CharField(source="biography_ne")
    biographyEnglish = serializers.CharField(source="biography_en")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta(CompactNarratorSerializer.Meta):
        fields = CompactNarratorSerializer.Meta.fields + (
            "biography",
            "biographyEnglish",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields
