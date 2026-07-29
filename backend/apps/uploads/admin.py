from django.contrib import admin, messages
from django.db.models import Prefetch, Q
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from rest_framework.exceptions import APIException
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
)

from apps.catalog.models import (
    AudioProcessingJob,
    AudioProcessingJobStatus,
    AudioTrack,
)
from apps.catalog.services import EditorialService
from apps.common.admin import ProtectedDeleteAdminMixin
from apps.common.admin_audio import SecureAudioPreviewAdminMixin
from apps.common.admin_performance import is_admin_changelist_request
from apps.common.admin_status import (
    ProcessingState,
    ProcessingStatusMediaMixin,
    processing_state_badge,
    upload_processing_state,
)
from apps.media_access.services import cloudfront_media_service
from apps.uploads.models import UploadSession, UploadStatus, UploadType
from apps.uploads.services import upload_session_service


def human_file_size(value):
    if value is None:
        return "—"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024


class UploadExpiryFilter(admin.SimpleListFilter):
    title = "expiry"
    parameter_name = "expiry"

    def lookups(self, request, model_admin):
        return (("active", "Active"), ("expired", "Expired"))

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(expires_at__gt=timezone.now())
        if self.value() == "expired":
            return queryset.filter(expires_at__lte=timezone.now())
        return queryset


class UploadProcessingStateFilter(admin.SimpleListFilter):
    title = "processing state"
    parameter_name = "processing_state"

    def lookups(self, request, model_admin):
        return ProcessingState.CHOICES

    def queryset(self, request, queryset):
        state = self.value()
        if state == ProcessingState.DRAFT:
            return queryset.filter(status=UploadStatus.PENDING)
        if state == ProcessingState.UPLOADED:
            return queryset.filter(
                status=UploadStatus.CONFIRMED,
                processing_jobs__isnull=True,
            )
        if state == ProcessingState.PUBLISHED:
            return queryset.filter(processing_jobs__track__is_published=True).distinct()
        if state in {
            ProcessingState.QUEUED,
            ProcessingState.PROCESSING,
            ProcessingState.READY,
        }:
            return queryset.filter(
                processing_jobs__track__is_published=False,
                processing_jobs__status=state,
            ).distinct()
        if state == ProcessingState.FAILED:
            return queryset.filter(
                Q(
                    status__in=(
                        UploadStatus.CANCELED,
                        UploadStatus.EXPIRED,
                        UploadStatus.ABANDONED,
                    )
                )
                | Q(processing_jobs__status=AudioProcessingJobStatus.FAILED)
            ).distinct()
        return queryset


@admin.register(UploadSession)
class UploadSessionAdmin(
    SecureAudioPreviewAdminMixin,
    ProcessingStatusMediaMixin,
    ProtectedDeleteAdminMixin,
    ModelAdmin,
):
    class Media:
        css = {
            "all": (
                "admin/css/secure-audio-preview.css",
                "admin/css/processing-status.css",
            )
        }
        js = ("admin/js/secure-audio-preview.js",)

    list_display = (
        "original_filename",
        "upload_type",
        "user",
        "expected_size_display",
        "actual_size_display",
        "content_type",
        "processing_badge",
        "created_at",
        "expires_at",
        "related_track_link",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("upload_type", ChoicesDropdownFilter),
        "content_type",
        ("user", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
        UploadExpiryFilter,
        UploadProcessingStateFilter,
    )
    search_fields = (
        "=id",
        "original_filename",
        "user__email",
        "user__display_name",
        "=processing_jobs__track__id",
        "processing_jobs__track__slug",
        "processing_jobs__track__title_ne",
        "processing_jobs__track__title_en",
        "processing_jobs__track__work__author__name_ne",
        "processing_jobs__track__work__author__name_en",
        "processing_jobs__track__narrator__name_ne",
        "processing_jobs__track__narrator__name_en",
    )
    exclude = ("object_key", "expected_size", "actual_size")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    actions = (
        "verify_uploads",
        "cancel_uploads",
        "mark_abandoned",
        "start_processing",
        "delete_temporary_objects",
    )
    readonly_fields = (
        "id",
        "user",
        "upload_type",
        "original_filename",
        "content_type",
        "expected_size_display",
        "actual_size_display",
        "status",
        "processing_badge",
        "expires_at",
        "related_track_link",
        "temporary_object_deleted_at",
        "created_at",
        "updated_at",
        "audio_preview",
    )

    def get_queryset(self, request):
        queryset = (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related(
                Prefetch(
                    "processing_jobs",
                    queryset=AudioProcessingJob.objects.select_related("track")
                    .defer(
                        "technical_error",
                        "track__description_ne",
                        "track__description_en",
                        "track__transcript",
                        "track__waveform_data",
                        "track__audio_master_file",
                        "track__stream_file_high",
                        "track__stream_file_low",
                    )
                    .order_by("-updated_at"),
                    to_attr="_prefetched_processing_jobs",
                )
            )
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer("object_key", "user__password", "user__avatar")
        return queryset

    @admin.display(description="Processing status")
    def processing_badge(self, obj):
        return processing_state_badge(upload_processing_state(obj))

    @admin.display(description="Secure audio preview")
    def audio_preview(self, obj):
        return self.render_audio_preview(obj)

    def get_audio_preview_sources(self, obj):
        has_original = (
            obj.upload_type == UploadType.AUDIO_MASTER
            and obj.status == UploadStatus.CONFIRMED
        )
        return [
            {"quality": "low", "label": "Low quality", "available": False},
            {"quality": "high", "label": "High quality", "available": False},
            {
                "quality": "original",
                "label": "Original upload",
                "available": has_original,
            },
        ]

    def get_audio_preview_title(self, obj):
        return obj.original_filename

    def resolve_audio_delivery(self, obj, *, quality, request):
        return cloudfront_media_service.deliver_admin_object(
            object_key=obj.object_key,
            quality=quality,
            user=request.user,
        )

    @admin.display(description="Expected size", ordering="expected_size")
    def expected_size_display(self, obj):
        return human_file_size(obj.expected_size)

    @admin.display(description="Actual size", ordering="actual_size")
    def actual_size_display(self, obj):
        return human_file_size(obj.actual_size)

    @admin.display(description="Related track")
    def related_track_link(self, obj):
        jobs = getattr(obj, "_prefetched_processing_jobs", ())
        if not jobs:
            return "—"
        job = jobs[0]
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:catalog_audiotrack_change", args=(job.track_id,)),
            job.track,
        )

    def _message_service_error(self, request, session, exc):
        detail = getattr(exc, "detail", "The operation could not be completed.")
        if isinstance(detail, dict):
            detail = " ".join(str(value) for value in detail.values())
        self.message_user(
            request,
            f"{session.original_filename}: {detail}",
            messages.ERROR,
        )

    def _confirmation(self, request, queryset, *, action, title, warning):
        if request.POST.get("confirmed") == "yes":
            return None
        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.model._meta,
            "sessions": queryset,
            "action_name": action,
            "warning": warning,
        }
        return TemplateResponse(
            request,
            "admin/uploads/uploadsession/action_confirmation.html",
            context,
        )

    @admin.action(description="Verify selected uploads")
    def verify_uploads(self, request, queryset):
        verified = 0
        for session in queryset:
            try:
                upload_session_service.confirm(session=session, actor=request.user)
                verified += 1
            except APIException as exc:
                self._message_service_error(request, session, exc)
        self.message_user(request, f"Verified {verified} upload(s).")

    @admin.action(description="Cancel selected uploads")
    def cancel_uploads(self, request, queryset):
        confirmation = self._confirmation(
            request,
            queryset,
            action="cancel_uploads",
            title="Confirm upload cancellation",
            warning=(
                "Cancellation removes pending temporary objects and cannot be undone."
            ),
        )
        if confirmation:
            return confirmation
        canceled = 0
        for session in queryset:
            try:
                upload_session_service.cancel(session=session, actor=request.user)
                canceled += 1
            except APIException as exc:
                self._message_service_error(request, session, exc)
        self.message_user(request, f"Canceled {canceled} upload(s).")

    @admin.action(description="Mark selected uploads abandoned")
    def mark_abandoned(self, request, queryset):
        confirmation = self._confirmation(
            request,
            queryset,
            action="mark_abandoned",
            title="Confirm abandoned uploads",
            warning=(
                "Abandoned uploads cannot be resumed. Stored objects are retained "
                "until an authorized deletion is separately confirmed."
            ),
        )
        if confirmation:
            return confirmation
        updated = 0
        for session in queryset:
            try:
                upload_session_service.mark_abandoned(
                    session=session,
                    actor=request.user,
                )
                updated += 1
            except APIException as exc:
                self._message_service_error(request, session, exc)
        self.message_user(request, f"Marked {updated} upload(s) abandoned.")

    @admin.action(
        description="Start processing selected audio uploads",
        permissions=("retry_processing",),
    )
    def start_processing(self, request, queryset):
        eligible_sessions = queryset.filter(
            status=UploadStatus.CONFIRMED,
            upload_type=UploadType.AUDIO_MASTER,
        )
        tracks = AudioTrack.objects.filter(
            processing_job__upload_session__in=eligible_sessions,
        )
        result = EditorialService.retry_processing(tracks, actor=request.user)
        self.message_user(
            request,
            f"Queued {result.updated} related track(s); skipped "
            f"{queryset.count() - result.updated} session(s) without an eligible "
            "failed track.",
            messages.SUCCESS if result.updated else messages.WARNING,
        )

    def has_retry_processing_permission(self, request):
        return request.user.has_perm("catalog.retry_audioprocessingjob")

    def has_delete_temporary_object_permission(self, request):
        return request.user.has_perm("uploads.delete_uploadsession")

    @admin.action(
        description="Delete selected temporary objects",
        permissions=("delete_temporary_object",),
    )
    def delete_temporary_objects(self, request, queryset):
        confirmation = self._confirmation(
            request,
            queryset,
            action="delete_temporary_objects",
            title="Confirm temporary object deletion",
            warning=(
                "This permanently deletes storage objects. Only canceled, expired, "
                "or abandoned uploads are eligible."
            ),
        )
        if confirmation:
            return confirmation
        deleted = 0
        for session in queryset:
            try:
                upload_session_service.delete_temporary_object(
                    session=session,
                    actor=request.user,
                )
                deleted += 1
            except APIException as exc:
                self._message_service_error(request, session, exc)
        self.message_user(request, f"Deleted {deleted} temporary object(s).")
