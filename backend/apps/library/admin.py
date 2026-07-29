from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.library.models import (
    FavoriteTrack,
    FollowedAuthor,
    FollowedNarrator,
    ListeningHistory,
    ListeningProgress,
    PlaybackEvent,
    PlaybackSession,
    SavedPlaylist,
    UserQueue,
    UserQueueItem,
)


class LibraryRelationshipAdmin(ModelAdmin):
    list_select_related = True
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(FavoriteTrack)
class FavoriteTrackAdmin(LibraryRelationshipAdmin):
    list_display = ("user", "track", "created_at")
    search_fields = ("user__email", "track__title_ne")
    autocomplete_fields = LibraryRelationshipAdmin.autocomplete_fields + ("track",)


@admin.register(SavedPlaylist)
class SavedPlaylistAdmin(LibraryRelationshipAdmin):
    list_display = ("user", "playlist", "created_at")
    search_fields = ("user__email", "playlist__title_ne")
    autocomplete_fields = LibraryRelationshipAdmin.autocomplete_fields + ("playlist",)


@admin.register(FollowedAuthor)
class FollowedAuthorAdmin(LibraryRelationshipAdmin):
    list_display = ("user", "author", "created_at")
    search_fields = ("user__email", "author__name_ne")
    autocomplete_fields = LibraryRelationshipAdmin.autocomplete_fields + ("author",)


@admin.register(FollowedNarrator)
class FollowedNarratorAdmin(LibraryRelationshipAdmin):
    list_display = ("user", "narrator", "created_at")
    search_fields = ("user__email", "narrator__name_ne")
    autocomplete_fields = LibraryRelationshipAdmin.autocomplete_fields + ("narrator",)


@admin.register(ListeningProgress)
class ListeningProgressAdmin(ModelAdmin):
    list_display = (
        "user",
        "track",
        "position_seconds",
        "duration_seconds",
        "progress_percentage",
        "is_completed",
        "last_listened_at",
    )
    list_filter = ("is_completed",)
    search_fields = ("user__email", "track__title_ne", "track__title_en")
    autocomplete_fields = ("user", "track")
    readonly_fields = (
        "position_seconds",
        "duration_seconds",
        "progress_percentage",
        "is_completed",
        "last_listened_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("user", "track")


class PlaybackEventInline(TabularInline):
    model = PlaybackEvent
    extra = 0
    readonly_fields = (
        "event_type",
        "occurred_at",
        "position_seconds",
        "deduplication_key",
        "metadata",
        "created_at",
        "updated_at",
    )
    can_delete = False


@admin.register(PlaybackSession)
class PlaybackSessionAdmin(ModelAdmin):
    list_display = (
        "user",
        "track",
        "device_id",
        "started_at",
        "ended_at",
        "listened_seconds",
        "completed",
    )
    list_filter = ("completed", "ended_at")
    search_fields = ("user__email", "track__title_ne", "device_id")
    list_select_related = ("user", "track")
    readonly_fields = (
        "user",
        "track",
        "device_id",
        "started_at",
        "last_activity_at",
        "ended_at",
        "listened_seconds",
        "completed",
        "created_at",
        "updated_at",
    )
    inlines = (PlaybackEventInline,)


@admin.register(ListeningHistory)
class ListeningHistoryAdmin(ModelAdmin):
    list_display = (
        "user",
        "track",
        "last_listened_at",
        "total_listened_seconds",
        "play_count",
        "completion_count",
    )
    search_fields = ("user__email", "track__title_ne")
    list_select_related = ("user", "track")
    readonly_fields = (
        "user",
        "track",
        "first_listened_at",
        "last_listened_at",
        "total_listened_seconds",
        "play_count",
        "completion_count",
        "created_at",
        "updated_at",
    )


@admin.register(PlaybackEvent)
class PlaybackEventAdmin(ModelAdmin):
    list_display = (
        "session",
        "event_type",
        "occurred_at",
        "position_seconds",
    )
    list_filter = ("event_type",)
    search_fields = ("session__user__email", "session__track__title_ne")
    list_select_related = ("session", "session__user", "session__track")
    readonly_fields = (
        "session",
        "event_type",
        "occurred_at",
        "position_seconds",
        "deduplication_key",
        "metadata",
        "created_at",
        "updated_at",
    )


class UserQueueItemInline(TabularInline):
    model = UserQueueItem
    extra = 0
    readonly_fields = ("track", "position", "created_at", "updated_at")
    can_delete = False


@admin.register(UserQueue)
class UserQueueAdmin(ModelAdmin):
    list_display = (
        "user",
        "current_index",
        "position_seconds",
        "is_shuffle_enabled",
        "repeat_mode",
        "updated_at",
    )
    search_fields = ("user__email",)
    list_filter = ("is_shuffle_enabled", "repeat_mode")
    list_select_related = ("user",)
    readonly_fields = (
        "user",
        "current_index",
        "position_seconds",
        "is_shuffle_enabled",
        "repeat_mode",
        "created_at",
        "updated_at",
    )
    inlines = (UserQueueItemInline,)


@admin.register(UserQueueItem)
class UserQueueItemAdmin(ModelAdmin):
    list_display = ("queue", "position", "track", "created_at")
    search_fields = ("queue__user__email", "track__title_ne")
    list_select_related = ("queue", "queue__user", "track")
    readonly_fields = ("queue", "track", "position", "created_at", "updated_at")
