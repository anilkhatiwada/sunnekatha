from rest_framework import serializers

from apps.catalog.models import AudioTrack
from apps.catalog.serializers import CatalogAuthorSummarySerializer
from apps.media_access.services import track_media_url_service
from apps.narrators.models import Narrator


class TrackNarratorSummarySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_ne")

    class Meta:
        model = Narrator
        fields = ("id", "slug", "name", "image")
        read_only_fields = fields


class CompactTrackSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne")
    titleEnglish = serializers.CharField(source="title_en")
    subtitle = serializers.CharField(source="work.subtitle_ne")
    contentType = serializers.CharField(source="content_type")
    author = CatalogAuthorSummarySerializer(source="work.author")
    narrator = TrackNarratorSummarySerializer()
    coverImage = serializers.SerializerMethodField()
    duration = serializers.IntegerField(source="duration_seconds")
    language = serializers.SlugRelatedField(read_only=True, slug_field="slug")
    genres = serializers.SerializerMethodField()
    moods = serializers.SerializerMethodField()
    playCount = serializers.IntegerField(source="play_count_cache")
    isPremium = serializers.BooleanField(source="is_premium")
    isExplicit = serializers.BooleanField(source="is_explicit")
    isFeatured = serializers.BooleanField(source="is_featured")
    publishedAt = serializers.DateTimeField(source="published_at")

    class Meta:
        model = AudioTrack
        fields = (
            "id",
            "slug",
            "title",
            "titleEnglish",
            "subtitle",
            "contentType",
            "author",
            "narrator",
            "coverImage",
            "duration",
            "language",
            "genres",
            "moods",
            "playCount",
            "isPremium",
            "isExplicit",
            "isFeatured",
            "publishedAt",
        )
        read_only_fields = fields

    def get_coverImage(self, obj: AudioTrack) -> str | None:
        cover = (
            obj.album.cover_image
            if obj.album_id and obj.album.cover_image
            else obj.work.cover_image
        )
        if not cover:
            return None
        request = self.context.get("request")
        url = cover.url
        return (
            request.build_absolute_uri(url) if request and url.startswith("/") else url
        )

    def get_genres(self, obj: AudioTrack) -> list[str]:
        return [genre.slug for genre in obj.work.genres.all()]

    def get_moods(self, obj: AudioTrack) -> list[str]:
        return [mood.slug for mood in obj.work.moods.all()]


class DetailedTrackSerializer(CompactTrackSerializer):
    description = serializers.CharField(source="description_ne")
    descriptionEnglish = serializers.CharField(source="description_en")
    chapterNumber = serializers.IntegerField(source="chapter_number")
    trackNumber = serializers.IntegerField(source="track_number")
    waveform = serializers.JSONField(source="waveform_data")
    transcript = serializers.CharField()
    processingStatus = serializers.CharField(source="processing_status")
    literaryWork = serializers.SerializerMethodField()
    album = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta(CompactTrackSerializer.Meta):
        fields = CompactTrackSerializer.Meta.fields + (
            "description",
            "descriptionEnglish",
            "chapterNumber",
            "trackNumber",
            "waveform",
            "transcript",
            "processingStatus",
            "literaryWork",
            "album",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields

    def get_literaryWork(self, obj: AudioTrack) -> dict[str, str | int | None]:
        return {
            "id": str(obj.work_id),
            "slug": obj.work.slug,
            "title": obj.work.title_ne,
            "titleEnglish": obj.work.title_en,
            "type": (
                "novel" if obj.work.content_type == "novel_chapter" else "collection"
            ),
            "contentType": obj.work.content_type,
            "chapterNumber": obj.chapter_number,
        }

    def get_album(self, obj: AudioTrack) -> dict[str, str] | None:
        if not obj.album_id:
            return None
        return {
            "id": str(obj.album_id),
            "slug": obj.album.slug,
            "title": obj.album.title_ne,
            "titleEnglish": obj.album.title_en,
        }


class PlayerTrackSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne")
    duration = serializers.IntegerField(source="duration_seconds")
    waveform = serializers.JSONField(source="waveform_data")
    isPremium = serializers.BooleanField(source="is_premium")
    media = serializers.SerializerMethodField()

    class Meta:
        model = AudioTrack
        fields = (
            "id",
            "slug",
            "title",
            "duration",
            "waveform",
            "isPremium",
            "media",
        )
        read_only_fields = fields

    def get_media(self, obj: AudioTrack) -> dict[str, str | None]:
        return track_media_url_service.get_access_urls(
            obj,
            request=self.context.get("request"),
        )
