from django.contrib import admin
from django.db.models import Count, Max
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.audio_ads.models import AudioAdvertisement, AudioAdvertisementPlayback


@admin.register(AudioAdvertisement)
class AudioAdvertisementAdmin(ModelAdmin):
    list_display = (
        "title",
        "is_enabled",
        "frequency_display",
        "duration_display",
        "total_plays_display",
        "latest_play_display",
        "updated_at",
    )
    list_filter = ("is_enabled", "frequency", "created_at", "updated_at")
    search_fields = ("title",)
    readonly_fields = (
        "id",
        "total_plays_display",
        "latest_play_display",
        "playback_history_link",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Advertisement", {"fields": ("title", "audio_file", "duration_seconds")}),
        ("Playback rules", {"fields": ("is_enabled", "frequency")}),
        (
            "Analytics",
            {
                "fields": (
                    "total_plays_display",
                    "latest_play_display",
                    "playback_history_link",
                )
            },
        ),
        (
            "System information",
            {"classes": ("collapse",), "fields": ("id", "created_at", "updated_at")},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _total_plays=Count("playbacks"),
                _latest_play=Max("playbacks__started_at"),
            )
        )

    @admin.display(description="Frequency", ordering="frequency")
    def frequency_display(self, obj):
        return f"Every {obj.frequency} audios"

    @admin.display(description="Duration", ordering="duration_seconds")
    def duration_display(self, obj):
        minutes, seconds = divmod(obj.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    @admin.display(description="Total plays", ordering="_total_plays")
    def total_plays_display(self, obj):
        annotated = getattr(obj, "_total_plays", None)
        return annotated if annotated is not None else obj.playbacks.count()

    @admin.display(description="Last played")
    def latest_play_display(self, obj):
        return getattr(obj, "_latest_play", None) or "Never"

    @admin.display(description="Playback history")
    def playback_history_link(self, obj):
        if not obj or not obj.pk:
            return "Available after saving."
        url = reverse("admin:audio_ads_audioadvertisementplayback_changelist")
        return format_html(
            '<a href="{}?advertisement__id__exact={}">View playback history</a>',
            url,
            obj.pk,
        )


@admin.register(AudioAdvertisementPlayback)
class AudioAdvertisementPlaybackAdmin(ModelAdmin):
    list_display = (
        "advertisement",
        "started_at",
        "track",
        "source",
        "user",
        "playback_sequence",
    )
    list_filter = ("advertisement", "source", "started_at")
    search_fields = (
        "advertisement__title",
        "track__title_ne",
        "track__title_en",
        "user__email",
    )
    readonly_fields = (
        "id",
        "advertisement",
        "started_at",
        "track",
        "source",
        "user",
        "session_id",
        "playback_sequence",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("audio_ads.view_audioadvertisementplayback")

    def has_delete_permission(self, request, obj=None):
        return False
