from urllib.parse import urlencode

from django.contrib import admin
from django.db.models import Count, Exists, OuterRef, Q
from django.urls import reverse
from django.utils.html import format_html
from rest_framework.exceptions import PermissionDenied
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter, RangeDateTimeFilter

from apps.catalog.models import AudioTrack
from apps.common.admin import ImagePreviewAdminMixin, ProtectedDeleteAdminMixin
from apps.common.admin_audio import SecureAudioPreviewAdminMixin
from apps.common.admin_performance import (
    is_admin_autocomplete_request,
    is_admin_changelist_request,
)
from apps.common.admin_search import RomanizedAliasAdminSearchMixin
from apps.media_access.services import cloudfront_media_service
from apps.narrators.models import Narrator
from apps.narrators.services import narrator_editorial_service
from apps.search.models import SearchEntityType


class LinkedAccountFilter(admin.SimpleListFilter):
    title = "linked account"
    parameter_name = "linked_account"

    def lookups(self, request, model_admin):
        return (("yes", "Linked"), ("no", "Not linked"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(user__isnull=False)
        if self.value() == "no":
            return queryset.filter(user__isnull=True)
        return queryset


class HasPublishedTracksFilter(admin.SimpleListFilter):
    title = "published tracks"
    parameter_name = "has_published_tracks"

    def lookups(self, request, model_admin):
        return (("yes", "Has published tracks"), ("no", "No published tracks"))

    def queryset(self, request, queryset):
        published = AudioTrack.objects.published().filter(narrator_id=OuterRef("pk"))
        queryset = queryset.annotate(_has_published_tracks=Exists(published))
        if self.value() == "yes":
            return queryset.filter(_has_published_tracks=True)
        if self.value() == "no":
            return queryset.filter(_has_published_tracks=False)
        return queryset


@admin.register(Narrator)
class NarratorAdmin(
    RomanizedAliasAdminSearchMixin,
    SecureAudioPreviewAdminMixin,
    ProtectedDeleteAdminMixin,
    ImagePreviewAdminMixin,
    ModelAdmin,
):
    list_display = (
        "image_thumbnail",
        "name_ne",
        "name_en",
        "user",
        "narrated_track_count",
        "follower_count_cache",
        "is_featured",
        "is_verified",
        "created_at",
    )
    list_filter = (
        ("is_featured", BooleanRadioFilter),
        ("is_verified", BooleanRadioFilter),
        LinkedAccountFilter,
        HasPublishedTracksFilter,
        ("created_at", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "slug",
        "name_ne",
        "name_en",
        "biography_ne",
        "biography_en",
        "user__email",
    )
    search_alias_mappings = ((SearchEntityType.NARRATOR, "id"),)
    autocomplete_fields = ("user",)
    readonly_fields = (
        "id",
        "slug",
        "follower_count_cache",
        "image_preview",
        "related_tracks_link",
        "public_profile_preview",
        "recent_narration_preview",
        "created_at",
        "updated_at",
    )
    actions = ("feature_selected", "unfeature_selected", "verify_selected")
    fieldsets = (
        (
            "Identity",
            {"fields": ("name_ne", "name_en", "slug")},
        ),
        (
            "Biography",
            {"fields": ("biography_ne", "biography_en")},
        ),
        (
            "Profile Image",
            {"fields": ("image", "image_preview")},
        ),
        (
            "Linked Account",
            {"fields": ("user",)},
        ),
        (
            "Editorial Status",
            {
                "fields": (
                    "is_featured",
                    "is_verified",
                    "public_profile_preview",
                )
            },
        ),
        (
            "Narrated Content",
            {"fields": ("related_tracks_link", "recent_narration_preview")},
        ),
        (
            "Statistics",
            {"fields": ("follower_count_cache",)},
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "slug", "name_ne", "name_en")
        queryset = queryset.select_related("user").annotate(
            _narrated_track_count=Count("audio_tracks", distinct=True)
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer("biography_ne", "biography_en", "user__password")
        return queryset

    @admin.display(description="Narrated tracks", ordering="_narrated_track_count")
    def narrated_track_count(self, obj):
        return obj._narrated_track_count

    @admin.display(description="Related tracks")
    def related_tracks_link(self, obj):
        if not obj:
            return "Available after the narrator is saved."
        url = reverse("admin:catalog_audiotrack_changelist")
        url = f"{url}?{urlencode({'narrator__id__exact': obj.pk})}"
        count = obj.audio_tracks.count()
        return format_html(
            '<a href="{}">Open {} narrated track(s) ↗</a>',
            url,
            count,
        )

    @admin.display(description="Public profile")
    def public_profile_preview(self, obj):
        if not obj or not obj.slug:
            return "Available after the narrator is saved."
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Preview public profile ↗</a>',
            reverse("narrators:detail", kwargs={"slug": obj.slug}),
        )

    def get_view_on_site_url(self, obj=None):
        if obj is None or not obj.slug:
            return None
        return reverse("narrators:detail", kwargs={"slug": obj.slug})

    def _recent_narration(self, obj):
        if obj is None or obj.pk is None:
            return None
        if hasattr(obj, "_admin_recent_narration"):
            return obj._admin_recent_narration
        track = (
            AudioTrack.objects.published()
            .filter(narrator=obj)
            .filter(Q(stream_file_high__gt="") | Q(stream_file_low__gt=""))
            .select_related("work", "narrator")
            .defer(
                "transcript",
                "waveform_data",
                "description_ne",
                "description_en",
                "audio_master_file",
            )
            .order_by("-published_at", "-created_at", "id")
            .first()
        )
        obj._admin_recent_narration = track
        return track

    @admin.display(description="Most recent narration")
    def recent_narration_preview(self, obj):
        return self.render_audio_preview(obj)

    def get_audio_preview_sources(self, obj):
        track = self._recent_narration(obj)
        return [
            {
                "quality": "low",
                "label": "Low quality",
                "available": bool(track and track.stream_file_low),
            },
            {
                "quality": "high",
                "label": "High quality",
                "available": bool(track and track.stream_file_high),
            },
        ]

    def get_audio_preview_title(self, obj):
        track = self._recent_narration(obj)
        return track.title_ne if track else f"{obj.name_ne} — no available narration"

    def get_audio_preview_duration(self, obj):
        track = self._recent_narration(obj)
        return track.duration_seconds if track else None

    def resolve_audio_delivery(self, obj, *, quality, request):
        if not request.user.has_perm("catalog.view_audiotrack"):
            raise PermissionDenied("Audio track access is required.")
        track = self._recent_narration(obj)
        if track is None:
            raise PermissionDenied("No authorized narration is available.")
        return cloudfront_media_service.deliver(
            track,
            quality=quality,
            request=request,
        )

    @admin.action(description="Feature selected narrators")
    def feature_selected(self, request, queryset):
        result = narrator_editorial_service.set_featured(
            queryset,
            value=True,
            actor=request.user,
        )
        self.message_user(request, f"Featured {result.updated} narrator(s).")

    @admin.action(description="Remove selected narrators from featured")
    def unfeature_selected(self, request, queryset):
        result = narrator_editorial_service.set_featured(
            queryset,
            value=False,
            actor=request.user,
        )
        self.message_user(request, f"Unfeatured {result.updated} narrator(s).")

    @admin.action(description="Verify selected narrators")
    def verify_selected(self, request, queryset):
        result = narrator_editorial_service.set_verified(
            queryset,
            actor=request.user,
        )
        self.message_user(request, f"Verified {result.updated} narrator(s).")
