from decimal import Decimal

from rest_framework import serializers

from apps.authors.serializers import CompactAuthorSerializer
from apps.catalog.track_serializers import CompactTrackSerializer
from apps.library.models import (
    ListeningHistory,
    ListeningProgress,
    PlaybackEventType,
    PlaybackSession,
    QueueRepeatMode,
    UserQueue,
    UserQueueItem,
)
from apps.narrators.serializers import CompactNarratorSerializer
from apps.playlists.serializers import CompactPlaylistSerializer


class FavoriteTrackSerializer(CompactTrackSerializer):
    is_favorited = serializers.BooleanField(default=True, read_only=True)

    class Meta(CompactTrackSerializer.Meta):
        fields = CompactTrackSerializer.Meta.fields + ("is_favorited",)


class SavedPlaylistSerializer(CompactPlaylistSerializer):
    is_playlist_saved = serializers.BooleanField(default=True, read_only=True)

    class Meta(CompactPlaylistSerializer.Meta):
        fields = CompactPlaylistSerializer.Meta.fields + ("is_playlist_saved",)


class FollowedAuthorSerializer(CompactAuthorSerializer):
    is_author_followed = serializers.BooleanField(default=True, read_only=True)

    class Meta(CompactAuthorSerializer.Meta):
        fields = CompactAuthorSerializer.Meta.fields + ("is_author_followed",)


class FollowedNarratorSerializer(CompactNarratorSerializer):
    is_narrator_followed = serializers.BooleanField(default=True, read_only=True)

    class Meta(CompactNarratorSerializer.Meta):
        fields = CompactNarratorSerializer.Meta.fields + ("is_narrator_followed",)


class TrackRelationshipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_favorited = serializers.BooleanField()


class PlaylistRelationshipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_playlist_saved = serializers.BooleanField()


class AuthorRelationshipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_author_followed = serializers.BooleanField()


class NarratorRelationshipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_narrator_followed = serializers.BooleanField()


class ListeningProgressSerializer(serializers.ModelSerializer):
    trackId = serializers.UUIDField(source="track_id", read_only=True)
    progressSeconds = serializers.FloatField(
        source="position_seconds",
        read_only=True,
    )
    durationSeconds = serializers.FloatField(
        source="duration_seconds",
        read_only=True,
    )
    progressPercentage = serializers.FloatField(
        source="progress_percentage",
        read_only=True,
    )
    isCompleted = serializers.BooleanField(source="is_completed", read_only=True)
    lastListenedAt = serializers.DateTimeField(
        source="last_listened_at",
        read_only=True,
    )
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = ListeningProgress
        fields = (
            "trackId",
            "progressSeconds",
            "durationSeconds",
            "progressPercentage",
            "isCompleted",
            "lastListenedAt",
            "updatedAt",
        )
        read_only_fields = fields


class ListeningProgressUpdateSerializer(serializers.Serializer):
    progressSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
    )
    durationSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        coerce_to_string=False,
    )


class ContinueListeningSerializer(serializers.ModelSerializer):
    track = CompactTrackSerializer()
    progress = ListeningProgressSerializer(source="*")

    class Meta:
        model = ListeningProgress
        fields = ("track", "progress")


class PlaybackSessionSerializer(serializers.ModelSerializer):
    trackId = serializers.UUIDField(source="track_id", read_only=True)
    deviceId = serializers.CharField(source="device_id", read_only=True)
    startedAt = serializers.DateTimeField(source="started_at", read_only=True)
    lastActivityAt = serializers.DateTimeField(
        source="last_activity_at",
        read_only=True,
    )
    endedAt = serializers.DateTimeField(source="ended_at", read_only=True)
    listenedSeconds = serializers.FloatField(
        source="listened_seconds",
        read_only=True,
    )

    class Meta:
        model = PlaybackSession
        fields = (
            "id",
            "trackId",
            "deviceId",
            "startedAt",
            "lastActivityAt",
            "endedAt",
            "listenedSeconds",
            "completed",
        )
        read_only_fields = fields


class StartPlaybackSessionSerializer(serializers.Serializer):
    trackId = serializers.UUIDField()
    deviceId = serializers.CharField(max_length=128, trim_whitespace=True)
    positionSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
        required=False,
        default=Decimal("0"),
    )
    clientEventId = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )


class UpdatePlaybackSessionSerializer(serializers.Serializer):
    listenedSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
    )
    eventType = serializers.ChoiceField(
        choices=(
            PlaybackEventType.RESUMED,
            PlaybackEventType.PAUSED,
            PlaybackEventType.SEEKED,
            PlaybackEventType.ERROR,
        ),
        required=False,
    )
    positionSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
        required=False,
    )
    clientEventId = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    metadata = serializers.JSONField(required=False)


class EndPlaybackSessionSerializer(serializers.Serializer):
    listenedSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
        required=False,
    )
    completed = serializers.BooleanField(required=False, default=False)
    positionSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
        required=False,
    )
    clientEventId = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )


class ListeningHistorySerializer(serializers.ModelSerializer):
    track = CompactTrackSerializer()
    firstListenedAt = serializers.DateTimeField(
        source="first_listened_at",
        read_only=True,
    )
    lastListenedAt = serializers.DateTimeField(
        source="last_listened_at",
        read_only=True,
    )
    totalListenedSeconds = serializers.FloatField(
        source="total_listened_seconds",
        read_only=True,
    )
    playCount = serializers.IntegerField(source="play_count", read_only=True)
    completionCount = serializers.IntegerField(
        source="completion_count",
        read_only=True,
    )

    class Meta:
        model = ListeningHistory
        fields = (
            "track",
            "firstListenedAt",
            "lastListenedAt",
            "totalListenedSeconds",
            "playCount",
            "completionCount",
        )


class RecentlyPlayedSerializer(serializers.ModelSerializer):
    track = CompactTrackSerializer()
    lastListenedAt = serializers.DateTimeField(
        source="last_listened_at",
        read_only=True,
    )

    class Meta:
        model = ListeningHistory
        fields = ("track", "lastListenedAt")


class UserQueueItemSerializer(serializers.ModelSerializer):
    track = CompactTrackSerializer()
    addedAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = UserQueueItem
        fields = ("id", "track", "position", "addedAt")
        read_only_fields = fields


class UserQueueSerializer(serializers.ModelSerializer):
    items = UserQueueItemSerializer(many=True)
    currentIndex = serializers.IntegerField(source="current_index", read_only=True)
    positionSeconds = serializers.FloatField(
        source="position_seconds",
        read_only=True,
    )
    isShuffleEnabled = serializers.BooleanField(
        source="is_shuffle_enabled",
        read_only=True,
    )
    repeatMode = serializers.CharField(source="repeat_mode", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = UserQueue
        fields = (
            "id",
            "items",
            "currentIndex",
            "positionSeconds",
            "isShuffleEnabled",
            "repeatMode",
            "updatedAt",
        )
        read_only_fields = fields


class ReplaceQueueSerializer(serializers.Serializer):
    trackIds = serializers.ListField(
        child=serializers.UUIDField(),
        max_length=500,
    )
    currentIndex = serializers.IntegerField(required=False, default=0)
    positionSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
        required=False,
        default=Decimal("0"),
    )


class QueueTrackSerializer(serializers.Serializer):
    trackId = serializers.UUIDField()


class ReorderQueueSerializer(serializers.Serializer):
    itemIds = serializers.ListField(
        child=serializers.UUIDField(),
        max_length=500,
    )


class QueuePositionSerializer(serializers.Serializer):
    currentIndex = serializers.IntegerField()
    positionSeconds = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        coerce_to_string=False,
    )


class QueueShuffleSerializer(serializers.Serializer):
    isShuffleEnabled = serializers.BooleanField()


class QueueRepeatSerializer(serializers.Serializer):
    repeatMode = serializers.ChoiceField(choices=QueueRepeatMode.choices)
