from rest_framework import serializers

from apps.authors.models import Author
from apps.catalog.models import Album
from apps.catalog.serializers import CatalogAuthorSummarySerializer
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist
from apps.taxonomy.models import Genre, Mood


class HomePlaylistSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne")
    coverImage = serializers.ImageField(source="cover_image")
    curatorName = serializers.SerializerMethodField()
    trackCount = serializers.IntegerField(read_only=True)
    totalDuration = serializers.IntegerField(read_only=True)
    category = serializers.CharField(source="playlist_type")
    isFeatured = serializers.BooleanField(source="is_featured")

    class Meta:
        model = Playlist
        fields = (
            "id",
            "slug",
            "title",
            "coverImage",
            "curatorName",
            "trackCount",
            "totalDuration",
            "category",
            "isFeatured",
        )
        read_only_fields = fields

    def get_curatorName(self, obj: Playlist) -> str:
        if obj.owner_id:
            return obj.owner.display_name or obj.owner.username
        return "SunneKatha"


class HomeAuthorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_ne")
    nameEnglish = serializers.CharField(source="name_en")
    isVerified = serializers.BooleanField(source="is_verified")

    class Meta:
        model = Author
        fields = ("id", "slug", "name", "nameEnglish", "image", "isVerified")
        read_only_fields = fields


class HomeNarratorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_ne")
    nameEnglish = serializers.CharField(source="name_en")
    followerCount = serializers.IntegerField(source="follower_count_cache")
    isVerified = serializers.BooleanField(source="is_verified")

    class Meta:
        model = Narrator
        fields = (
            "id",
            "slug",
            "name",
            "nameEnglish",
            "image",
            "followerCount",
            "isVerified",
        )
        read_only_fields = fields


class HomeMoodCollectionSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="name_ne")
    titleEnglish = serializers.CharField(source="name_en")
    coverImage = serializers.ImageField(source="image")
    trackCount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Mood
        fields = (
            "id",
            "slug",
            "title",
            "titleEnglish",
            "coverImage",
            "trackCount",
        )
        read_only_fields = fields


class HomeGenreSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="name_ne")
    titleEnglish = serializers.CharField(source="name_en")
    coverImage = serializers.ImageField(source="image")

    class Meta:
        model = Genre
        fields = (
            "id",
            "slug",
            "title",
            "titleEnglish",
            "coverImage",
        )
        read_only_fields = fields


class HomeAlbumSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne")
    titleEnglish = serializers.CharField(source="title_en")
    coverImage = serializers.ImageField(source="cover_image")
    author = CatalogAuthorSummarySerializer()
    albumType = serializers.CharField(source="album_type")
    releaseDate = serializers.DateField(source="release_date")

    class Meta:
        model = Album
        fields = (
            "id",
            "slug",
            "title",
            "titleEnglish",
            "coverImage",
            "author",
            "albumType",
            "releaseDate",
        )
        read_only_fields = fields


class HomeResponseSerializer(serializers.Serializer):
    hero = serializers.JSONField(allow_null=True)
    sections = serializers.ListField(child=serializers.JSONField())
