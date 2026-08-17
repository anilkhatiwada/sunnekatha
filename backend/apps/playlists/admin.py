import json
from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q, Sum
from django.forms.models import BaseInlineFormSet
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from rest_framework.exceptions import APIException
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
)

from apps.catalog.admin import AudioTrackAdmin
from apps.catalog.models import AudioTrack, TrackProcessingStatus
from apps.catalog.services import EditorialService
from apps.common.admin import (
    CoverPreviewAdminMixin,
    ProtectedDeleteAdminMixin,
    ServiceManagedFeaturedAdminMixin,
)
from apps.common.admin_actions import confirm_bulk_action
from apps.common.admin_performance import (
    is_admin_autocomplete_request,
    is_admin_changelist_request,
)
from apps.common.admin_search import RomanizedAliasAdminSearchMixin
from apps.home.editorial_services import home_editorial_service
from apps.media_access.services import cloudfront_media_service
from apps.playlists.models import Playlist, PlaylistItem
from apps.playlists.services import playlist_item_service
from apps.search.models import SearchEntityType


class PlaylistItemAdminFormSet(BaseInlineFormSet):
    """Translate inline intent into the transactional playlist service API."""

    admin_user = None

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        desired_tracks = [
            form.cleaned_data["track"]
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if len({track.pk for track in desired_tracks}) != len(desired_tracks):
            raise ValidationError("Each track may appear only once in a playlist.")
        positions = [
            form.cleaned_data["position"]
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if len(set(positions)) != len(positions):
            raise ValidationError(
                "Each playlist item must have a unique integer position."
            )
        if self.instance.is_published:
            if not desired_tracks:
                raise ValidationError(
                    "Published playlists must contain at least one ready track."
                )
            now = timezone.now()
            unavailable = [
                track.title_ne
                for track in desired_tracks
                if not (
                    track.is_published
                    and track.processing_status == TrackProcessingStatus.READY
                    and track.published_at
                    and track.published_at <= now
                )
            ]
            if unavailable:
                raise ValidationError(
                    "Published playlists may contain only published, ready tracks. "
                    f"Unavailable: {', '.join(unavailable[:5])}."
                )

    def save(self, commit=True):
        if not commit:
            raise ValueError("Playlist item changes require an atomic service save.")
        desired = []
        for index, form in enumerate(self.forms):
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            desired.append(
                (
                    form.cleaned_data["position"],
                    index,
                    form.cleaned_data["track"],
                )
            )
        desired.sort(key=lambda row: (row[0], row[1]))
        desired_tracks = [row[2] for row in desired]
        desired_ids = {track.pk for track in desired_tracks}
        current = list(
            PlaylistItem.objects.filter(playlist=self.instance).select_related("track")
        )
        current_ids = {item.track_id for item in current}

        for item in current:
            if item.track_id not in desired_ids:
                playlist_item_service.remove(
                    playlist=self.instance,
                    track=item.track,
                    actor=self.admin_user,
                )
        for track in desired_tracks:
            if track.pk not in current_ids:
                playlist_item_service.add(
                    playlist=self.instance,
                    track=track,
                    user=self.admin_user,
                )
        playlist_item_service.reorder(
            playlist=self.instance,
            track_ids=[track.pk for track in desired_tracks],
            actor=self.admin_user,
        )
        self.new_objects = []
        self.changed_objects = []
        self.deleted_objects = []
        return list(
            PlaylistItem.objects.filter(playlist=self.instance)
            .select_related("track")
            .order_by("position")
        )


class PlaylistItemAdminForm(forms.ModelForm):
    class Meta:
        model = PlaylistItem
        fields = ("position", "track")

    def _get_validation_exclusions(self):
        exclusions = super()._get_validation_exclusions()
        # Position swaps are validated as a complete formset and then applied
        # through PlaylistItemService. Per-row constraint checks would reject a
        # valid swap against the still-persisted neighboring row.
        exclusions.add("position")
        return exclusions


class PlaylistItemInline(TabularInline):
    model = PlaylistItem
    extra = 1
    autocomplete_fields = ("track",)
    ordering = ("position", "created_at", "id")
    fields = (
        "position",
        "track",
        "track_duration",
        "track_narrator",
        "track_author",
        "processing_status",
        "created_at",
    )
    readonly_fields = (
        "track_duration",
        "track_narrator",
        "track_author",
        "processing_status",
        "created_at",
    )
    show_change_link = True
    formset = PlaylistItemAdminFormSet
    form = PlaylistItemAdminForm
    ordering_field = "position"
    hide_ordering_field = False

    def get_formset(self, request, obj=None, **kwargs):
        base_formset = super().get_formset(request, obj, **kwargs)
        user = request.user

        class RequestPlaylistItemFormSet(base_formset):
            admin_user = user

        return RequestPlaylistItemFormSet

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("track__narrator", "track__work__author")
            .defer(
                "track__transcript",
                "track__waveform_data",
                "track__description_ne",
                "track__description_en",
                "track__audio_master_file",
                "track__stream_file_high",
                "track__stream_file_low",
            )
        )

    @admin.display(description="Duration")
    def track_duration(self, obj):
        return AudioTrackAdmin.format_duration(obj.track.duration_seconds)

    @admin.display(description="Narrator")
    def track_narrator(self, obj):
        return obj.track.narrator

    @admin.display(description="Author")
    def track_author(self, obj):
        return obj.track.work.author

    @admin.display(description="Processing")
    def processing_status(self, obj):
        return obj.track.get_processing_status_display()


@admin.register(Playlist)
class PlaylistAdmin(
    RomanizedAliasAdminSearchMixin,
    ServiceManagedFeaturedAdminMixin,
    ProtectedDeleteAdminMixin,
    CoverPreviewAdminMixin,
    ModelAdmin,
):
    inline_track_limit = 100
    preview_track_limit = 100

    class Media:
        css = {"all": ("admin/css/album-play-all.css",)}
        js = ("admin/js/album-play-all.js",)

    list_display = (
        "cover_thumbnail",
        "title_ne",
        "playlist_type",
        "visibility",
        "owner",
        "track_count",
        "total_duration",
        "is_featured",
        "is_published",
        "updated_at",
    )
    list_filter = (
        ("playlist_type", ChoicesDropdownFilter),
        ("visibility", ChoicesDropdownFilter),
        ("is_featured", BooleanRadioFilter),
        ("is_published", BooleanRadioFilter),
        ("owner", AutocompleteSelectFilter),
        ("updated_at", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "title_ne",
        "title_en",
        "slug",
        "owner__email",
        "owner__display_name",
    )
    search_alias_mappings = ((SearchEntityType.PLAYLIST, "id"),)
    autocomplete_fields = ("owner",)
    readonly_fields = (
        "id",
        "slug",
        "cover_preview",
        "is_published",
        "publication_readiness",
        "ordered_tracks_link",
        "playlist_preview",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Basic information",
            {"fields": ("title_ne", "title_en", "slug", "playlist_type", "owner")},
        ),
        (
            "Cover image",
            {"fields": ("cover_image", "cover_preview")},
        ),
        (
            "Description",
            {"fields": ("description_ne", "description_en")},
        ),
        (
            "Visibility",
            {"fields": ("visibility",)},
        ),
        (
            "Featured status",
            {"fields": ("is_featured",)},
        ),
        (
            "Publication settings",
            {"fields": ("is_published", "publication_readiness")},
        ),
        (
            "Ordered tracks",
            {"fields": ("ordered_tracks_link", "playlist_preview")},
        ),
        (
            "System information",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )
    inlines = (PlaylistItemInline,)
    actions = (
        "play_playlist_preview",
        "duplicate_selected",
        "publish_selected",
        "unpublish_selected",
        "feature_selected",
        "unfeature_selected",
        "add_to_new_playlists_homepage",
        "recalculate_positions",
        "remove_unavailable_tracks",
    )

    def get_urls(self):
        return [
            path(
                "<uuid:object_id>/preview/<uuid:track_id>/<str:quality>/",
                self.admin_site.admin_view(self.preview_delivery_view),
                name="playlists_playlist_preview_delivery",
            )
        ] + super().get_urls()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "slug", "title_ne", "title_en")
        queryset = queryset.select_related("owner").annotate(
            _track_count=Count("items", distinct=True),
            _total_duration=Sum("items__track__duration_seconds"),
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer(
                "description_ne",
                "description_en",
                "owner__password",
                "owner__avatar",
            )
        return queryset

    @admin.display(description="Tracks", ordering="_track_count")
    def track_count(self, obj):
        return obj._track_count

    @admin.display(description="Total duration", ordering="_total_duration")
    def total_duration(self, obj):
        return AudioTrackAdmin.format_duration(obj._total_duration or 0)

    def get_inline_instances(self, request, obj=None):
        count = getattr(obj, "_track_count", None)
        if obj is not None and count is None:
            count = obj.items.count()
        if count is not None and count > self.inline_track_limit:
            return []
        return super().get_inline_instances(request, obj)

    @admin.display(description="Track management")
    def ordered_tracks_link(self, obj):
        if not obj:
            return "Available after the playlist is saved."
        count = getattr(obj, "_track_count", None)
        if count is None:
            count = obj.items.count()
        url = reverse("admin:playlists_playlistitem_changelist")
        note = (
            f" Inline hidden above {self.inline_track_limit} tracks."
            if count > self.inline_track_limit
            else ""
        )
        return format_html(
            '<a href="{}?{}">Manage all {} ordered tracks ↗</a>{}',
            url,
            urlencode({"playlist__id__exact": obj.pk}),
            count,
            note,
        )

    @admin.display(description="Publication readiness")
    def publication_readiness(self, obj):
        if not obj or not obj.pk:
            return "Add tracks before publishing."
        now = timezone.now()
        items = PlaylistItem.objects.filter(playlist=obj)
        if not items.exists():
            return "Blocked: a published playlist must contain at least one track."
        unavailable = items.filter(
            Q(track__is_published=False)
            | ~Q(track__processing_status=TrackProcessingStatus.READY)
            | Q(track__published_at__isnull=True)
            | Q(track__published_at__gt=now)
            | (Q(track__stream_file_low="") & Q(track__stream_file_high=""))
        ).count()
        if unavailable:
            return f"Blocked: {unavailable} track(s) are unpublished or unready."
        return "Ready to publish."

    @admin.action(description="Add to New Playlists homepage section")
    def add_to_new_playlists_homepage(self, request, queryset):
        try:
            section, added = home_editorial_service.add_new_playlists(
                playlists=queryset,
                actor=request.user,
            )
        except (PermissionDenied, ValidationError) as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        self.message_user(
            request,
            f"Added {added} playlist(s) to {section.title_en or section.title_ne}.",
        )

    def _preview_items(self, obj):
        if not obj or not obj.pk:
            return [], False
        if hasattr(obj, "_admin_preview_items"):
            return obj._admin_preview_items
        items = list(
            PlaylistItem.objects.filter(playlist=obj)
            .filter(
                Q(track__stream_file_low__gt="") | Q(track__stream_file_high__gt="")
            )
            .select_related("track")
            .defer(
                "track__transcript",
                "track__waveform_data",
                "track__description_ne",
                "track__description_en",
                "track__audio_master_file",
            )
            .order_by("position", "created_at", "id")[: self.preview_track_limit + 1]
        )
        result = (
            items[: self.preview_track_limit],
            len(items) > self.preview_track_limit,
        )
        obj._admin_preview_items = result
        return result

    @admin.display(description="Play playlist preview")
    def playlist_preview(self, obj):
        if not obj or not obj.pk:
            return "Available after the playlist is saved."
        items, truncated = self._preview_items(obj)
        manifest = []
        for item in items:
            track = item.track
            qualities = []
            for quality, available in (
                ("low", bool(track.stream_file_low)),
                ("high", bool(track.stream_file_high)),
            ):
                if available:
                    qualities.append(
                        {
                            "quality": quality,
                            "url": reverse(
                                "admin:playlists_playlist_preview_delivery",
                                kwargs={
                                    "object_id": obj.pk,
                                    "track_id": track.pk,
                                    "quality": quality,
                                },
                            ),
                        }
                    )
            manifest.append(
                {
                    "id": str(track.pk),
                    "title": track.title_ne,
                    "duration": track.duration_seconds,
                    "qualities": qualities,
                }
            )
        return mark_safe(
            render_to_string(
                "admin/catalog/album/play_all_preview.html",
                {
                    "album": obj,
                    "tracks": [item.track for item in items],
                    "manifest_json": json.dumps(manifest),
                    "truncated": truncated,
                    "limit": self.preview_track_limit,
                },
            )
        )

    def preview_delivery_view(self, request, object_id, track_id, quality):
        playlist = self.get_object(request, object_id)
        if playlist is None:
            raise Http404
        if not self.has_view_or_change_permission(request, playlist):
            raise PermissionDenied
        if not request.user.has_perm("catalog.view_audiotrack"):
            raise PermissionDenied
        track = (
            AudioTrack.objects.filter(pk=track_id, playlist_items__playlist=playlist)
            .select_related("narrator")
            .first()
        )
        if track is None:
            raise Http404
        try:
            delivery = cloudfront_media_service.deliver(
                track, quality=quality, request=request
            )
        except APIException as exc:
            response = JsonResponse(
                {
                    "detail": str(exc.detail),
                    "code": getattr(exc, "default_code", "media_delivery_error"),
                },
                status=exc.status_code,
            )
        else:
            expires_at = delivery.get("expiresAt")
            response = JsonResponse(
                {
                    "quality": delivery["quality"],
                    "url": delivery["url"],
                    "expiresAt": expires_at.isoformat() if expires_at else None,
                }
            )
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        return response

    @admin.action(description="Play selected playlist preview")
    def play_playlist_preview(self, request, queryset):
        playlist = queryset.first()
        if queryset.count() != 1 or playlist is None:
            self.message_user(
                request,
                "Select exactly one playlist to open its preview.",
                messages.WARNING,
            )
            return None
        return HttpResponseRedirect(
            f"{reverse('admin:playlists_playlist_change', args=(playlist.pk,))}"
            "#playlist-preview"
        )

    @admin.action(description="Duplicate selected playlists as drafts")
    def duplicate_selected(self, request, queryset):
        duplicates = [
            playlist_item_service.duplicate(playlist=playlist, user=request.user)
            for playlist in queryset
        ]
        self.message_user(request, f"Created {len(duplicates)} draft copy/copies.")

    @admin.action(description="Publish selected ready playlists")
    def publish_selected(self, request, queryset):
        updated, skipped = playlist_item_service.set_published(
            queryset,
            value=True,
            actor=request.user,
        )
        self.message_user(
            request,
            f"Published {updated}; skipped {skipped} empty or unavailable playlist(s).",
        )

    @admin.action(description="Unpublish selected playlists")
    def unpublish_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="unpublish_selected",
                title="Unpublish selected playlists",
                warning=("Selected playlists will immediately leave public listings."),
                submit_label="Unpublish playlists",
            )
        updated, skipped = playlist_item_service.set_published(
            queryset,
            value=False,
            actor=request.user,
        )
        self.message_user(
            request, f"Unpublished {updated}; skipped {skipped} draft playlist(s)."
        )

    @admin.action(description="Feature selected editorial playlists")
    def feature_selected(self, request, queryset):
        result = EditorialService.set_featured(
            queryset,
            value=True,
            actor=request.user,
        )
        self.message_user(
            request,
            f"Featured {result.updated}; skipped {result.skipped} non-editorial "
            "or unchanged playlist(s).",
        )

    @admin.action(description="Remove selected playlists from featured")
    def unfeature_selected(self, request, queryset):
        result = EditorialService.set_featured(
            queryset,
            value=False,
            actor=request.user,
        )
        self.message_user(request, f"Unfeatured {result.updated} playlist(s).")

    @admin.action(description="Recalculate selected playlist positions")
    def recalculate_positions(self, request, queryset):
        changed = sum(
            playlist_item_service.recalculate_positions(
                playlist=playlist,
                actor=request.user,
            )
            for playlist in queryset
        )
        self.message_user(request, f"Recalculated {changed} item position(s).")

    @admin.action(description="Remove unavailable tracks from selected playlists")
    def remove_unavailable_tracks(self, request, queryset):
        removed = sum(
            playlist_item_service.remove_unavailable(
                playlist=playlist,
                actor=request.user,
            )
            for playlist in queryset
        )
        self.message_user(request, f"Removed {removed} unavailable track(s).")


@admin.register(PlaylistItem)
class PlaylistItemAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "playlist",
        "position",
        "track",
        "track_duration",
        "narrator",
        "author",
        "processing_status",
        "added_by",
        "created_at",
    )
    list_filter = (
        ("playlist", AutocompleteSelectFilter),
        ("track__processing_status", ChoicesDropdownFilter),
    )
    search_fields = (
        "=id",
        "=track__id",
        "playlist__slug",
        "playlist__title_ne",
        "playlist__title_en",
        "track__slug",
        "track__title_ne",
        "track__title_en",
        "track__narrator__name_ne",
        "track__narrator__name_en",
        "track__work__author__name_ne",
        "track__work__author__name_en",
    )
    autocomplete_fields = ("playlist", "track", "added_by")
    list_select_related = (
        "playlist",
        "track",
        "track__narrator",
        "track__work__author",
        "added_by",
    )
    ordering = ("playlist", "position", "created_at", "id")

    @admin.display(description="Duration")
    def track_duration(self, obj):
        return AudioTrackAdmin.format_duration(obj.track.duration_seconds)

    @admin.display(description="Narrator")
    def narrator(self, obj):
        return obj.track.narrator

    @admin.display(description="Author")
    def author(self, obj):
        return obj.track.work.author

    @admin.display(description="Processing")
    def processing_status(self, obj):
        return obj.track.get_processing_status_display()
