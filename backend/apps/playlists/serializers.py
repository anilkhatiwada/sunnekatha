from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from apps.catalog.models import AudioTrack, LiteraryWork, WorkStructure
from apps.catalog.serializers import CompactLiteraryWorkSerializer
from apps.catalog.track_serializers import CompactTrackSerializer
from apps.common.serializers import RejectUnknownFieldsMixin
from apps.playlists.models import (
    Playlist,
    PlaylistItem,
    PlaylistType,
    PlaylistVisibility,
)


class CompactPlaylistSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title_ne", read_only=True)
    titleEnglish = serializers.CharField(source="title_en", read_only=True)
    coverImage = serializers.ImageField(source="cover_image", read_only=True)
    curatorName = serializers.SerializerMethodField()
    trackCount = serializers.IntegerField(read_only=True)
    totalDuration = serializers.IntegerField(read_only=True)
    category = serializers.CharField(source="playlist_type", read_only=True)
    playlistType = serializers.CharField(source="playlist_type", read_only=True)
    isFeatured = serializers.BooleanField(source="is_featured", read_only=True)
    isPublished = serializers.BooleanField(source="is_published", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    isOwnedByCurrentUser = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = (
            "id",
            "slug",
            "title",
            "titleEnglish",
            "coverImage",
            "curatorName",
            "trackCount",
            "totalDuration",
            "category",
            "playlistType",
            "visibility",
            "isFeatured",
            "isPublished",
            "createdAt",
            "updatedAt",
            "isOwnedByCurrentUser",
        )
        read_only_fields = fields

    def get_curatorName(self, obj: Playlist) -> str:
        if obj.owner_id:
            return obj.owner.display_name or obj.owner.username
        return "SunneKatha"

    def get_isOwnedByCurrentUser(self, obj: Playlist) -> bool:
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and obj.owner_id == request.user.id
        )


class PlaylistSerializer(CompactPlaylistSerializer):
    description = serializers.CharField(source="description_ne", read_only=True)
    descriptionEnglish = serializers.CharField(
        source="description_en",
        read_only=True,
    )

    class Meta(CompactPlaylistSerializer.Meta):
        fields = CompactPlaylistSerializer.Meta.fields + (
            "description",
            "descriptionEnglish",
        )
        read_only_fields = fields


class PlaylistDetailSerializer(PlaylistSerializer):
    tracks = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta(PlaylistSerializer.Meta):
        fields = PlaylistSerializer.Meta.fields + ("items", "tracks")

    def get_items(self, obj: Playlist) -> list[dict]:
        result = []
        for item in obj.items.all():
            if item.track_id:
                result.append(
                    {
                        "id": str(item.id),
                        "position": item.position,
                        "kind": "track",
                        "content": CompactTrackSerializer(
                            item.track, context=self.context
                        ).data,
                    }
                )
            elif item.work_id:
                result.append(
                    {
                        "id": str(item.id),
                        "position": item.position,
                        "kind": "work",
                        "content": CompactLiteraryWorkSerializer(
                            item.work, context=self.context
                        ).data,
                    }
                )
        return result

    def get_tracks(self, obj: Playlist) -> list[dict]:
        tracks = []
        for item in obj.items.all():
            if item.track_id:
                tracks.append(item.track)
            elif item.work_id:
                tracks.extend(getattr(item.work, "public_chapters", ()))
        return CompactTrackSerializer(tracks, many=True, context=self.context).data


class PlaylistWriteSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    titleNe = serializers.CharField(source="title_ne")
    titleEn = serializers.CharField(
        source="title_en",
        required=False,
        allow_blank=True,
    )
    descriptionNe = serializers.CharField(
        source="description_ne",
        required=False,
        allow_blank=True,
    )
    descriptionEn = serializers.CharField(
        source="description_en",
        required=False,
        allow_blank=True,
    )
    coverImage = serializers.ImageField(
        source="cover_image",
        required=False,
        allow_null=True,
    )
    playlistType = serializers.ChoiceField(
        source="playlist_type",
        choices=PlaylistType.choices,
        required=False,
    )
    isFeatured = serializers.BooleanField(source="is_featured", required=False)
    isPublished = serializers.BooleanField(source="is_published", required=False)

    class Meta:
        model = Playlist
        fields = (
            "titleNe",
            "titleEn",
            "descriptionNe",
            "descriptionEn",
            "coverImage",
            "playlistType",
            "visibility",
            "isFeatured",
            "isPublished",
        )

    def validate(self, attrs):
        user = self.context["request"].user
        playlist_type = attrs.get(
            "playlist_type",
            self.instance.playlist_type if self.instance else PlaylistType.USER,
        )
        if playlist_type != PlaylistType.USER and not user.is_staff:
            raise serializers.ValidationError(
                {"playlistType": "Only staff can manage non-user playlists."}
            )
        if not user.is_staff and ("is_featured" in attrs or "is_published" in attrs):
            raise serializers.ValidationError(
                "Only staff can change publication and featured status."
            )
        visibility = attrs.get(
            "visibility",
            self.instance.visibility if self.instance else PlaylistVisibility.PRIVATE,
        )
        if (
            playlist_type == PlaylistType.USER
            and visibility == PlaylistVisibility.PUBLIC
        ):
            raise serializers.ValidationError(
                {
                    "visibility": (
                        "Personal playlists may be private or unlisted. Only "
                        "SunneKatha editorial playlists can be public."
                    )
                }
            )
        if (
            attrs.get(
                "is_featured",
                self.instance.is_featured if self.instance else False,
            )
            and playlist_type != PlaylistType.EDITORIAL
        ):
            raise serializers.ValidationError(
                {"isFeatured": "Only editorial playlists can be featured."}
            )
        if (
            self.instance
            and "playlist_type" in attrs
            and playlist_type != self.instance.playlist_type
        ):
            raise serializers.ValidationError(
                {"playlistType": "Playlist type cannot be changed."}
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        playlist_type = validated_data.get("playlist_type", PlaylistType.USER)
        validated_data["owner"] = user if playlist_type == PlaylistType.USER else None
        if playlist_type == PlaylistType.USER:
            validated_data.setdefault("visibility", PlaylistVisibility.PRIVATE)
        validated_data.setdefault(
            "is_published",
            playlist_type == PlaylistType.USER,
        )
        return super().create(validated_data)


class AddTrackSerializer(serializers.Serializer):
    trackId = serializers.PrimaryKeyRelatedField(
        source="track",
        queryset=AudioTrack.objects.all(),
    )

    def validate_trackId(self, track):
        if not (
            AudioTrack.objects.published()
            .filter(pk=track.pk)
            .filter(Q(stream_file_low__gt="") | Q(stream_file_high__gt=""))
            .exists()
        ):
            raise serializers.ValidationError("Track is not publicly playable.")
        return track


class RemoveTrackSerializer(AddTrackSerializer):
    pass


class AddWorkSerializer(serializers.Serializer):
    workId = serializers.PrimaryKeyRelatedField(
        source="work", queryset=LiteraryWork.objects.all()
    )

    def validate_workId(self, work):
        if (
            work.structure != WorkStructure.SERIALIZED
            or not LiteraryWork.objects.discoverable().filter(pk=work.pk).exists()
        ):
            raise serializers.ValidationError(
                "Work is not a publicly playable serialized work."
            )
        return work


class RemoveWorkSerializer(AddWorkSerializer):
    pass


class ReorderTracksSerializer(serializers.Serializer):
    trackIds = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
    )


class VisibilitySerializer(serializers.Serializer):
    visibility = serializers.ChoiceField(choices=PlaylistVisibility.choices)

    def validate_visibility(self, value):
        playlist = self.context.get("playlist")
        if (
            playlist
            and playlist.playlist_type == PlaylistType.USER
            and value == PlaylistVisibility.PUBLIC
        ):
            raise serializers.ValidationError(
                "Personal playlists may be private or unlisted."
            )
        return value


class DuplicatePlaylistSerializer(serializers.Serializer):
    titleNe = serializers.CharField(required=False, allow_blank=False)

    @transaction.atomic
    def save(self, **kwargs):
        source = self.context["source"]
        user = self.context["request"].user
        title = self.validated_data.get("titleNe", f"{source.title_ne} (प्रतिलिपि)")
        duplicate = Playlist.objects.create(
            owner=user,
            title_ne=title,
            title_en=source.title_en,
            description_ne=source.description_ne,
            description_en=source.description_en,
            playlist_type=PlaylistType.USER,
            visibility=PlaylistVisibility.PRIVATE,
            is_published=True,
        )
        PlaylistItem.objects.bulk_create(
            [
                PlaylistItem(
                    playlist=duplicate,
                    track=item.track,
                    work=item.work,
                    position=item.position,
                    added_by=user,
                )
                for item in source.items.all()
            ]
        )
        return duplicate
