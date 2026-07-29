from rest_framework import serializers

from apps.authors.models import Author
from apps.catalog.models import Album, LiteraryWork


class CatalogAuthorSummarySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_ne")
    nameEnglish = serializers.CharField(source="name_en")

    class Meta:
        model = Author
        fields = ("id", "slug", "name", "nameEnglish", "image")
        read_only_fields = fields


class CompactLiteraryWorkSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne")
    titleEnglish = serializers.CharField(source="title_en")
    subtitle = serializers.CharField(source="subtitle_ne")
    subtitleEnglish = serializers.CharField(source="subtitle_en")
    contentType = serializers.CharField(source="content_type")
    author = CatalogAuthorSummarySerializer()
    language = serializers.SlugRelatedField(read_only=True, slug_field="slug")
    genres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="slug",
    )
    moods = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="slug",
    )
    publicationYear = serializers.IntegerField(source="publication_year")
    coverImage = serializers.ImageField(source="cover_image")
    isFeatured = serializers.BooleanField(source="is_featured")
    publishedAt = serializers.DateTimeField(source="published_at")

    class Meta:
        model = LiteraryWork
        fields = (
            "id",
            "slug",
            "title",
            "titleEnglish",
            "subtitle",
            "subtitleEnglish",
            "contentType",
            "author",
            "language",
            "genres",
            "moods",
            "publicationYear",
            "coverImage",
            "isFeatured",
            "publishedAt",
        )
        read_only_fields = fields


class LiteraryWorkSerializer(CompactLiteraryWorkSerializer):
    description = serializers.CharField(source="description_ne")
    descriptionEnglish = serializers.CharField(source="description_en")
    copyrightStatus = serializers.CharField(source="copyright_status")
    copyrightOwner = serializers.CharField(source="copyright_owner")
    licenseNotes = serializers.CharField(source="license_notes")
    isPublished = serializers.BooleanField(source="is_published")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta(CompactLiteraryWorkSerializer.Meta):
        fields = CompactLiteraryWorkSerializer.Meta.fields + (
            "description",
            "descriptionEnglish",
            "copyrightStatus",
            "copyrightOwner",
            "licenseNotes",
            "isPublished",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields


class CompactAlbumSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne")
    titleEnglish = serializers.CharField(source="title_en")
    coverImage = serializers.ImageField(source="cover_image")
    author = CatalogAuthorSummarySerializer()
    albumType = serializers.CharField(source="album_type")
    genres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="slug",
    )
    moods = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="slug",
    )
    releaseDate = serializers.DateField(source="release_date")
    isFeatured = serializers.BooleanField(source="is_featured")

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
            "genres",
            "moods",
            "releaseDate",
            "isFeatured",
        )
        read_only_fields = fields


class AlbumSerializer(CompactAlbumSerializer):
    description = serializers.CharField(source="description_ne")
    descriptionEnglish = serializers.CharField(source="description_en")
    isPublished = serializers.BooleanField(source="is_published")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta(CompactAlbumSerializer.Meta):
        fields = CompactAlbumSerializer.Meta.fields + (
            "description",
            "descriptionEnglish",
            "isPublished",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields
