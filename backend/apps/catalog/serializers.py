from rest_framework import serializers

from apps.authors.models import Author
from apps.catalog.models import Album, LiteraryWork
from apps.taxonomy.serializers import ContentCategorySerializer, TagSerializer


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
    category = ContentCategorySerializer()
    primaryCategory = ContentCategorySerializer(source="category")
    categories = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    contentType = serializers.CharField(source="category.slug")
    structure = serializers.CharField()
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
    chapterCount = serializers.SerializerMethodField()
    totalDuration = serializers.SerializerMethodField()

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
            "category",
            "primaryCategory",
            "categories",
            "tags",
            "structure",
            "author",
            "language",
            "genres",
            "moods",
            "publicationYear",
            "coverImage",
            "isFeatured",
            "publishedAt",
            "chapterCount",
            "totalDuration",
        )
        read_only_fields = fields

    def get_chapterCount(self, obj: LiteraryWork) -> int:
        return int(getattr(obj, "playable_chapter_count", 0))

    def get_totalDuration(self, obj: LiteraryWork) -> int:
        return int(getattr(obj, "playable_total_duration", 0) or 0)

    def get_categories(self, obj: LiteraryWork) -> list[dict]:
        values = [obj.category, *obj.categories.all()]
        unique = {category.pk: category for category in values}
        return ContentCategorySerializer(unique.values(), many=True).data


class LiteraryWorkSerializer(CompactLiteraryWorkSerializer):
    description = serializers.CharField(source="description_ne")
    descriptionEnglish = serializers.CharField(source="description_en")
    copyrightStatus = serializers.CharField(source="copyright_status")
    copyrightOwner = serializers.CharField(source="copyright_owner")
    licenseNotes = serializers.CharField(source="license_notes")
    isPublished = serializers.BooleanField(source="is_published")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    chapters = serializers.SerializerMethodField()

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
            "chapters",
        )
        read_only_fields = fields

    def get_chapters(self, obj: LiteraryWork) -> list[dict]:
        from apps.catalog.track_serializers import CompactTrackSerializer

        chapters = getattr(obj, "public_chapters", None)
        if chapters is None:
            chapters = obj.audio_tracks.published().order_by(
                "chapter_number", "track_number", "published_at", "id"
            )
        return CompactTrackSerializer(
            chapters,
            many=True,
            context=self.context,
        ).data


class CatalogItemSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("track", "work"))
    content = serializers.SerializerMethodField()

    def get_content(self, obj: dict) -> dict:
        if obj["kind"] == "work":
            return CompactLiteraryWorkSerializer(
                obj["content"], context=self.context
            ).data
        from apps.catalog.track_serializers import CompactTrackSerializer

        return CompactTrackSerializer(obj["content"], context=self.context).data


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
