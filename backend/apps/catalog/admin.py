import json
from datetime import timedelta
from pathlib import PurePosixPath

from botocore.exceptions import ClientError
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from rest_framework.exceptions import APIException
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    MultipleChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RangeNumericFilter,
)
from unfold.decorators import action, display
from unfold.enums import ActionVariant

from apps.catalog.models import (
    Album,
    AudioProcessingJob,
    AudioProcessingJobStatus,
    AudioProcessingStage,
    AudioTrack,
    CopyrightLicense,
    CopyrightStatus,
    LiteraryWork,
    PendingReviewTrack,
    PermissionDocument,
    PermissionDocumentAudit,
    RightsHolder,
    TrackProcessingStatus,
    TrackReviewEvent,
    TrackReviewStatus,
)
from apps.catalog.review_workflow import (
    pending_review_service,
    review_attention_issues,
    track_review_workflow,
)
from apps.catalog.rights_services import permission_document_service
from apps.catalog.scheduled_publications import (
    scheduled_publication_admin_service,
)
from apps.catalog.services import EditorialService
from apps.catalog.tasks import queue_audio_processing
from apps.common.admin import CoverPreviewAdminMixin, ProtectedDeleteAdminMixin
from apps.common.admin_actions import (
    confirm_bulk_action,
    export_metadata_csv,
    report_bulk_action,
    run_object_action,
)
from apps.common.admin_audio import SecureAudioPreviewAdminMixin
from apps.common.admin_performance import (
    is_admin_autocomplete_request,
    is_admin_changelist_request,
)
from apps.common.admin_search import RomanizedAliasAdminSearchMixin
from apps.common.admin_status import (
    ProcessingState,
    ProcessingStatusMediaMixin,
    processing_state_badge,
    track_processing_state,
)
from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAuditAction
from apps.creators.models import ContentContributor
from apps.media_access.services import cloudfront_media_service
from apps.search.models import SearchEntityType


class PermissionDocumentAdminForm(forms.ModelForm):
    document = forms.FileField(
        required=False,
        widget=forms.FileInput,
        help_text=(
            "Existing private files are never linked directly. Upload a file only "
            "when replacing the stored document."
        ),
    )

    class Meta:
        model = PermissionDocument
        fields = (
            "license",
            "title",
            "document_type",
            "document",
            "is_verified",
            "uploaded_by",
            "verified_by",
            "verified_at",
            "notes",
        )

    def clean_document(self):
        uploaded = self.cleaned_data.get("document")
        if uploaded:
            return uploaded
        if self.instance.pk and self.instance.document:
            return self.instance.document
        raise forms.ValidationError("A permission document is required.")


class EditorialActionMixin:
    @action(
        description="Feature selected",
        icon="star",
        permissions=("change",),
    )
    def feature_selected(self, request, queryset):
        def feature(obj):
            result = EditorialService.set_featured(
                queryset.model._base_manager.filter(pk=obj.pk),
                value=True,
                actor=request.user,
            )
            if result.updated != 1:
                raise ValidationError("Item is already featured or is not eligible.")

        report = run_object_action(
            model_admin=self,
            request=request,
            queryset=queryset,
            operation=feature,
        )
        report_bulk_action(self, request, verb="Featured", report=report)

    @action(
        description="Unfeature selected",
        icon="star_border",
        permissions=("change",),
    )
    def unfeature_selected(self, request, queryset):
        def unfeature(obj):
            result = EditorialService.set_featured(
                queryset.model._base_manager.filter(pk=obj.pk),
                value=False,
                actor=request.user,
            )
            if result.updated != 1:
                raise ValidationError("Item is not currently featured.")

        report = run_object_action(
            model_admin=self,
            request=request,
            queryset=queryset,
            operation=unfeature,
        )
        report_bulk_action(self, request, verb="Unfeatured", report=report)


class CatalogAdminBase(
    RomanizedAliasAdminSearchMixin,
    ProtectedDeleteAdminMixin,
    CoverPreviewAdminMixin,
    EditorialActionMixin,
    ModelAdmin,
):
    search_fields = (
        "=id",
        "title_ne",
        "title_en",
        "slug",
        "author__name_ne",
        "author__name_en",
    )
    autocomplete_fields = ("author",)
    filter_horizontal = ("genres", "moods")
    readonly_fields = (
        "id",
        "slug",
        "cover_preview",
        "is_featured",
        "is_published",
        "created_at",
        "updated_at",
    )
    actions = (
        "publish_selected",
        "unpublish_selected",
        "feature_selected",
        "unfeature_selected",
    )


class ReviewReasonForm(forms.Form):
    reason = forms.CharField(
        label="Editorial reason",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="This comment is recorded in the audit trail and sent to creators.",
    )


class ReviewScheduleForm(forms.Form):
    scheduled_for = forms.DateTimeField(
        label="Publication date and time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Choose a future publication time.",
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class AssignReviewerForm(forms.Form):
    reviewer = forms.ModelChoiceField(queryset=get_user_model().objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reviewer"].queryset = (
            get_user_model()
            .objects.filter(is_active=True, is_staff=True)
            .filter(
                Q(is_superuser=True)
                | Q(
                    user_permissions__content_type__app_label="catalog",
                    user_permissions__codename="approve_audiotrack",
                )
                | Q(
                    groups__permissions__content_type__app_label="catalog",
                    groups__permissions__codename="approve_audiotrack",
                )
            )
            .distinct()
            .order_by("display_name", "email")
        )


class TrackReviewEventInline(TabularInline):
    model = TrackReviewEvent
    extra = 0
    can_delete = False
    fields = (
        "from_status",
        "to_status",
        "actor",
        "comment",
        "scheduled_for",
        "created_at",
    )
    readonly_fields = fields
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("actor")


@admin.register(TrackReviewEvent)
class TrackReviewEventAdmin(ModelAdmin):
    list_display = (
        "track",
        "from_status",
        "to_status",
        "actor",
        "created_at",
    )
    list_filter = ("from_status", "to_status", "created_at")
    search_fields = (
        "=id",
        "=track__id",
        "track__slug",
        "track__title_ne",
        "track__title_en",
        "actor__email",
        "comment",
    )
    list_select_related = ("track", "actor")
    readonly_fields = (
        "id",
        "track",
        "from_status",
        "to_status",
        "actor",
        "comment",
        "scheduled_for",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PendingCreatorFilter(admin.SimpleListFilter):
    title = "creator or uploader"
    parameter_name = "creator"

    def lookups(self, request, model_admin):
        users = (
            get_user_model()
            .objects.filter(
                Q(
                    creator_profile__contributions__track__review_status=(
                        TrackReviewStatus.SUBMITTED
                    )
                )
                | Q(
                    upload_sessions__processing_jobs__track__review_status=(
                        TrackReviewStatus.SUBMITTED
                    )
                )
                | Q(
                    narrator_profile__audio_tracks__review_status=(
                        TrackReviewStatus.SUBMITTED
                    )
                )
            )
            .distinct()
            .order_by("display_name", "email")
        )
        return [(str(user.pk), str(user)) for user in users]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(
            Q(contributors__creator__user_id=self.value())
            | Q(processing_job__upload_session__user_id=self.value())
            | Q(narrator__user_id=self.value())
        ).distinct()


class ExpiringSoonFilter(admin.SimpleListFilter):
    title = "expiring soon"
    parameter_name = "expiring_soon"

    def lookups(self, request, model_admin):
        return (("yes", "Within 30 days"), ("no", "Not within 30 days"))

    def queryset(self, request, queryset):
        today = timezone.localdate()
        expiring = Q(
            expiration_date__gte=today,
            expiration_date__lte=today + timedelta(days=30),
        )
        if self.value() == "yes":
            return queryset.filter(expiring)
        if self.value() == "no":
            return queryset.exclude(expiring)
        return queryset


class ExpiredPermissionFilter(admin.SimpleListFilter):
    title = "expired"
    parameter_name = "expired"

    def lookups(self, request, model_admin):
        return (("yes", "Expired"), ("no", "Not expired"))

    def queryset(self, request, queryset):
        expired = Q(expiration_date__lt=timezone.localdate()) | Q(
            literary_work__copyright_status=CopyrightStatus.PERMISSION_EXPIRED
        )
        if self.value() == "yes":
            return queryset.filter(expired)
        if self.value() == "no":
            return queryset.exclude(expired)
        return queryset


class MissingDocumentsFilter(admin.SimpleListFilter):
    title = "permission documents"
    parameter_name = "missing_documents"

    def lookups(self, request, model_admin):
        return (("yes", "Missing documents"), ("no", "Has documents"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(documents__isnull=True)
        if self.value() == "no":
            return queryset.filter(documents__isnull=False).distinct()
        return queryset


class PublicationStatusFilter(admin.SimpleListFilter):
    title = "publication status"
    parameter_name = "publication_state"

    def lookups(self, request, model_admin):
        return (
            ("published", "Published"),
            ("scheduled", "Scheduled"),
            ("draft", "Draft"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "published":
            return queryset.filter(is_published=True, published_at__lte=now)
        if self.value() == "scheduled":
            return queryset.filter(is_published=True, published_at__gt=now)
        if self.value() == "draft":
            return queryset.filter(is_published=False)
        return queryset


class TrackProcessingStateFilter(admin.SimpleListFilter):
    title = "processing state"
    parameter_name = "processing_state"

    def lookups(self, request, model_admin):
        return ProcessingState.CHOICES

    def queryset(self, request, queryset):
        state = self.value()
        if state == ProcessingState.PUBLISHED:
            return queryset.filter(is_published=True)
        if state == ProcessingState.FAILED:
            return queryset.filter(
                Q(processing_status=TrackProcessingStatus.FAILED)
                | Q(processing_job__status=AudioProcessingJobStatus.FAILED)
            ).distinct()
        if state == ProcessingState.PROCESSING:
            return queryset.filter(
                Q(processing_status=TrackProcessingStatus.PROCESSING)
                | Q(processing_job__status=AudioProcessingJobStatus.PROCESSING)
            ).distinct()
        if state == ProcessingState.READY:
            return queryset.filter(
                is_published=False,
                processing_status=TrackProcessingStatus.READY,
            )
        if state == ProcessingState.QUEUED:
            return queryset.filter(
                is_published=False,
                processing_job__status=AudioProcessingJobStatus.QUEUED,
            )
        if state == ProcessingState.UPLOADED:
            return queryset.filter(
                is_published=False,
                processing_job__isnull=True,
            ).exclude(audio_master_file="")
        if state == ProcessingState.DRAFT:
            return queryset.filter(
                is_published=False,
                processing_job__isnull=True,
                audio_master_file="",
            ).exclude(
                processing_status__in=(
                    TrackProcessingStatus.PROCESSING,
                    TrackProcessingStatus.READY,
                    TrackProcessingStatus.FAILED,
                )
            )
        return queryset


class LiteraryWorkTrackInline(TabularInline):
    model = AudioTrack
    fk_name = "work"
    extra = 0
    fields = (
        "track_number",
        "title_ne",
        "narrator",
        "processing_status",
        "review_status",
        "is_published",
    )
    readonly_fields = fields
    ordering = ("track_number", "chapter_number", "title_ne")
    show_change_link = True
    verbose_name_plural = "Related audio tracks"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("narrator")
            .defer(
                "transcript",
                "waveform_data",
                "description_ne",
                "description_en",
                "audio_master_file",
                "stream_file_high",
                "stream_file_low",
            )
        )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PermissionDocumentInline(TabularInline):
    model = PermissionDocument
    extra = 0
    fields = (
        "title",
        "document_type",
        "is_verified",
        "verified_by",
        "verified_at",
        "document_record_link",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Document record")
    def document_record_link(self, obj):
        if not obj or not obj.pk:
            return "Available after saving."
        return format_html(
            '<a href="{}">Open secure document record ↗</a>',
            reverse("admin:catalog_permissiondocument_change", args=(obj.pk,)),
        )


@admin.register(RightsHolder)
class RightsHolderAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = ("name", "contact_email", "country", "is_verified", "created_at")
    list_filter = (("is_verified", BooleanRadioFilter), "country")
    search_fields = ("=id", "name", "contact_email", "country")
    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "name")
        return queryset


@admin.register(CopyrightLicense)
class CopyrightLicenseAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "literary_work",
        "copyright_status",
        "rights_holder",
        "permission_type",
        "effective_date",
        "expiration_date",
        "territory",
        "allows_monetization",
        "allows_audio",
        "document_availability",
        "verification_status",
        "date_warning",
    )
    list_filter = (
        ("literary_work__copyright_status", MultipleChoicesDropdownFilter),
        ExpiringSoonFilter,
        ExpiredPermissionFilter,
        ("rights_holder", AutocompleteSelectFilter),
        ("permission_type", ChoicesDropdownFilter),
        MissingDocumentsFilter,
        ("verification_status", ChoicesDropdownFilter),
        ("expiration_date", RangeDateFilter),
    )
    search_fields = (
        "=id",
        "literary_work__title_ne",
        "literary_work__title_en",
        "literary_work__slug",
        "rights_holder__name",
        "territory",
    )
    autocomplete_fields = ("literary_work", "rights_holder")
    readonly_fields = ("id", "document_availability", "created_at", "updated_at")
    list_select_related = ("literary_work", "rights_holder")
    inlines = (PermissionDocumentInline,)
    fieldsets = (
        (
            "Stored rights record",
            {
                "fields": (
                    "literary_work",
                    "rights_holder",
                    "permission_type",
                    "territory",
                ),
                "description": (
                    "This page records supplied rights information and workflow "
                    "status. It does not determine legal validity."
                ),
            },
        ),
        (
            "Permission period",
            {"fields": ("effective_date", "expiration_date")},
        ),
        (
            "Granted uses",
            {"fields": ("allows_audio", "allows_monetization")},
        ),
        (
            "Verification",
            {
                "fields": (
                    "verification_status",
                    "document_availability",
                    "internal_notes",
                )
            },
        ),
        (
            "System information",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = (
            super()
            .get_queryset(request)
            .select_related("literary_work", "rights_holder")
        )
        if is_admin_autocomplete_request(request):
            return queryset.only(
                "id",
                "permission_type",
                "literary_work__id",
                "literary_work__title_ne",
                "rights_holder__id",
                "rights_holder__name",
            )
        queryset = queryset.annotate(_document_count=Count("documents", distinct=True))
        if is_admin_changelist_request(request):
            queryset = queryset.defer(
                "internal_notes",
                "literary_work__description_ne",
                "literary_work__description_en",
                "literary_work__license_notes",
                "literary_work__cover_image",
                "rights_holder__notes",
            )
        return queryset

    @admin.display(
        description="Copyright status",
        ordering="literary_work__copyright_status",
    )
    def copyright_status(self, obj):
        return obj.literary_work.get_copyright_status_display()

    @admin.display(description="Documents", ordering="_document_count")
    def document_availability(self, obj):
        count = getattr(obj, "_document_count", None)
        if count is None:
            count = obj.documents.count()
        return f"{count} document(s)" if count else "Missing"

    @display(
        description="Date status",
        label={"current": "success", "expiring": "warning", "expired": "danger"},
    )
    def date_warning(self, obj):
        if not obj.expiration_date:
            return ("current", "No expiration stored")
        remaining = (obj.expiration_date - timezone.localdate()).days
        if remaining < 0:
            return ("expired", "Expired")
        if remaining <= 30:
            return ("expiring", f"Expires in {remaining} days")
        return ("current", "Current")


@admin.register(PermissionDocument)
class PermissionDocumentAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    form = PermissionDocumentAdminForm
    list_display = (
        "title",
        "document_type",
        "rights_holder",
        "literary_work",
        "effective_date",
        "expiration_date",
        "uploaded_by",
        "is_verified",
        "verified_by",
        "verified_at",
        "expiry_warning",
        "secure_download",
        "safe_preview",
    )
    list_filter = (
        ("document_type", ChoicesDropdownFilter),
        ("is_verified", BooleanRadioFilter),
        ("license__rights_holder", AutocompleteSelectFilter),
        ("license__expiration_date", RangeDateFilter),
        ("verified_at", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "title",
        "license__literary_work__title_ne",
        "license__literary_work__title_en",
        "license__literary_work__slug",
        "license__rights_holder__name",
    )
    autocomplete_fields = ("license",)
    readonly_fields = (
        "id",
        "stored_file_status",
        "secure_download",
        "safe_preview",
        "expiry_warning",
        "uploaded_by",
        "is_verified",
        "verified_by",
        "verified_at",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "license",
        "license__literary_work",
        "license__rights_holder",
        "verified_by",
    )
    actions = ("verify_selected", "revoke_verification_selected")
    fieldsets = (
        (
            "Document",
            {
                "fields": (
                    "title",
                    "document_type",
                    "license",
                    "document",
                    "stored_file_status",
                    "secure_download",
                    "safe_preview",
                )
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "is_verified",
                    "verified_by",
                    "verified_at",
                    "expiry_warning",
                )
            },
        ),
        ("Notes", {"fields": ("notes",)}),
        (
            "System information",
            {
                "classes": ("collapse",),
                "fields": ("id", "uploaded_by", "created_at", "updated_at"),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<uuid:object_id>/secure-document/<str:mode>/",
                self.admin_site.admin_view(self.secure_document_view),
                name="catalog_permissiondocument_secure",
            )
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        if not change and obj.uploaded_by_id is None:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Rights holder", ordering="license__rights_holder")
    def rights_holder(self, obj):
        return obj.license.rights_holder or "—"

    @admin.display(
        description="Literary work",
        ordering="license__literary_work__title_ne",
    )
    def literary_work(self, obj):
        return obj.license.literary_work

    @admin.display(description="Effective", ordering="license__effective_date")
    def effective_date(self, obj):
        return obj.license.effective_date or "Not stored"

    @admin.display(description="Expiration", ordering="license__expiration_date")
    def expiration_date(self, obj):
        return obj.license.expiration_date or "Not stored"

    @display(
        description="Expiry",
        label={"current": "success", "expiring": "warning", "expired": "danger"},
    )
    def expiry_warning(self, obj):
        expiration = obj.license.expiration_date
        if not expiration:
            return ("current", "No expiration stored")
        remaining = (expiration - timezone.localdate()).days
        if remaining < 0:
            return ("expired", "Expired")
        if remaining <= 30:
            return ("expiring", f"Expires in {remaining} days")
        return ("current", "Current")

    @admin.display(description="Stored file")
    def stored_file_status(self, obj):
        if not obj or not obj.pk:
            return "Available after saving."
        return "Private file stored" if obj.document else "No file stored"

    def _secure_link(self, obj, *, mode, label):
        if not obj or not obj.pk or not obj.document:
            return "Unavailable"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            reverse(
                "admin:catalog_permissiondocument_secure",
                args=(obj.pk, mode),
            ),
            label,
        )

    @admin.display(description="Secure download")
    def secure_download(self, obj):
        return self._secure_link(obj, mode="download", label="Download securely ↗")

    @admin.display(description="Preview")
    def safe_preview(self, obj):
        if not obj or not obj.document:
            return "Unavailable"
        suffix = PurePosixPath(obj.document.name).suffix.lower()
        if suffix not in {".pdf", ".jpg", ".jpeg", ".png"}:
            return "Preview unavailable for this document type."
        return self._secure_link(obj, mode="preview", label="Preview securely ↗")

    def secure_document_view(self, request, object_id, mode):
        document = self.get_object(request, object_id)
        if document is None:
            raise Http404
        if not self.has_view_or_change_permission(request, document):
            raise PermissionDenied
        if mode not in {"download", "preview"}:
            raise Http404
        if not document.document:
            raise Http404
        if mode == "preview":
            suffix = PurePosixPath(document.document.name).suffix.lower()
            if suffix not in {".pdf", ".jpg", ".jpeg", ".png"}:
                raise Http404
        try:
            delivery = cloudfront_media_service.deliver_admin_document(
                object_key=document.document.name,
                user=request.user,
            )
            permission_document_service.record_download(
                document=document,
                actor=getattr(request, "user", None),
                preview=mode == "preview",
            )
        except APIException as exc:
            response = JsonResponse(
                {
                    "detail": str(exc.detail),
                    "code": getattr(exc, "default_code", "document_delivery_error"),
                },
                status=exc.status_code,
            )
        else:
            response = HttpResponseRedirect(delivery["url"])
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        return response

    def has_verify_permission(self, request):
        return request.user.has_perm("catalog.verify_permissiondocument")

    @admin.action(
        description="Verify selected permission documents",
        permissions=("verify",),
    )
    def verify_selected(self, request, queryset):
        updated = permission_document_service.verify(
            queryset=queryset,
            actor=request.user,
        )
        self.message_user(request, f"Verified {updated} document(s).")

    @admin.action(
        description="Revoke verification for selected documents",
        permissions=("verify",),
    )
    def revoke_verification_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="revoke_verification_selected",
                title="Revoke permission-document verification",
                warning=(
                    "Verification status will be removed and the change will be "
                    "recorded in the rights audit trail."
                ),
                submit_label="Revoke verification",
            )
        updated = permission_document_service.revoke_verification(
            queryset=queryset,
            actor=request.user,
        )
        self.message_user(request, f"Revoked verification for {updated} document(s).")


@admin.register(PermissionDocumentAudit)
class PermissionDocumentAuditAdmin(ModelAdmin):
    list_display = ("document", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = (
        "document__title",
        "document__license__literary_work__title_ne",
        "actor__email",
    )
    list_select_related = ("document", "actor")
    readonly_fields = (
        "id",
        "document",
        "actor",
        "action",
        "details",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LiteraryWork)
class LiteraryWorkAdmin(CatalogAdminBase):
    list_display = (
        "cover_thumbnail",
        "title_ne",
        "title_en",
        "category",
        "author",
        "language",
        "copyright_status",
        "track_count",
        "publication_badge",
        "featured_badge",
        "published_at",
    )
    list_filter = (
        ("category", AutocompleteSelectFilter),
        PublicationStatusFilter,
        ("is_featured", BooleanRadioFilter),
        ("copyright_status", MultipleChoicesDropdownFilter),
        ("language", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("publication_year", RangeNumericFilter),
        ("published_at", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "slug",
        "title_ne",
        "title_en",
        "author__name_ne",
        "author__name_en",
        "copyright_owner",
    )
    search_alias_mappings = (
        (SearchEntityType.LITERARY_WORK, "id"),
        (SearchEntityType.AUTHOR, "author_id"),
    )
    autocomplete_fields = CatalogAdminBase.autocomplete_fields + ("language",)
    readonly_fields = CatalogAdminBase.readonly_fields + (
        "published_at",
        "preview_public_page",
    )
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "title_ne",
                    "title_en",
                    "subtitle_ne",
                    "subtitle_en",
                    "slug",
                )
            },
        ),
        (
            "Author and Classification",
            {
                "fields": (
                    "author",
                    "category",
                    "language",
                    "genres",
                    "moods",
                    "publication_year",
                )
            },
        ),
        (
            "Description",
            {"fields": ("description_ne", "description_en")},
        ),
        (
            "Copyright and Rights",
            {
                "fields": (
                    "copyright_status",
                    "copyright_owner",
                    "license_notes",
                )
            },
        ),
        (
            "Artwork",
            {"fields": ("cover_image", "cover_preview")},
        ),
        (
            "Publication",
            {
                "fields": (
                    "is_published",
                    "is_featured",
                    "published_at",
                    "preview_public_page",
                )
            },
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )
    inlines = (LiteraryWorkTrackInline,)
    date_hierarchy = "published_at"
    list_select_related = ("author", "language")
    actions = CatalogAdminBase.actions + ("duplicate_selected",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "slug", "title_ne", "title_en")
        queryset = queryset.select_related("author", "language").annotate(
            _track_count=Count("audio_tracks", distinct=True)
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer(
                "description_ne",
                "description_en",
                "license_notes",
                "author__biography_ne",
                "author__biography_en",
                "author__image",
                "language__description",
                "language__image",
            )
        return queryset

    @admin.display(description="Tracks", ordering="_track_count")
    def track_count(self, obj):
        return obj._track_count

    @display(
        description="Publication status",
        ordering="is_published",
        label={
            "published": "success",
            "scheduled": "warning",
            "draft": "info",
        },
    )
    def publication_badge(self, obj):
        if not obj.is_published:
            return ("draft", "Draft")
        if obj.published_at and obj.published_at > timezone.now():
            return ("scheduled", "Scheduled")
        return ("published", "Published")

    @display(
        description="Featured",
        ordering="is_featured",
        label={"featured": "warning", "standard": "info"},
    )
    def featured_badge(self, obj):
        return ("featured", "Featured") if obj.is_featured else ("standard", "Standard")

    @admin.display(description="Public preview")
    def preview_public_page(self, obj):
        if not obj or not obj.slug:
            return "Available after the work is saved."
        if (
            not obj.is_published
            or not obj.published_at
            or obj.published_at > timezone.now()
        ):
            return "Available when the work is publicly published."
        url = reverse("catalog:work-detail", kwargs={"slug": obj.slug})
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Preview public page ↗</a>',
            url,
        )

    def get_view_on_site_url(self, obj=None):
        if (
            obj is None
            or not obj.is_published
            or not obj.published_at
            or obj.published_at > timezone.now()
        ):
            return None
        return reverse("catalog:work-detail", kwargs={"slug": obj.slug})

    @admin.action(description="Publish selected literary works")
    def publish_selected(self, request, queryset):
        targets = list(queryset.filter(is_published=False))
        result = EditorialService.publish_works(queryset, actor=request.user)
        for work in targets:
            administrative_audit_service.record(
                actor=getattr(request, "user", None),
                action=AdministrativeAuditAction.PUBLISHED,
                obj=work,
                reason="Literary work published.",
                before={"is_published": False},
                after={"is_published": True},
                request_identifier=getattr(request, "request_identifier", ""),
            )
        self.message_user(
            request,
            f"Published {result.updated}; skipped {result.skipped} already "
            "published work(s).",
        )

    @admin.action(description="Unpublish selected literary works")
    def unpublish_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="unpublish_selected",
                title="Unpublish selected literary works",
                warning="Selected works will immediately leave the public catalog.",
                submit_label="Unpublish works",
            )
        targets = list(queryset.filter(is_published=True))
        result = EditorialService.unpublish_works(queryset, actor=request.user)
        for work in targets:
            administrative_audit_service.record(
                actor=getattr(request, "user", None),
                action=AdministrativeAuditAction.UNPUBLISHED,
                obj=work,
                reason="Literary work unpublished.",
                before={"is_published": True},
                after={"is_published": False},
                request_identifier=getattr(request, "request_identifier", ""),
            )
        self.message_user(
            request,
            f"Unpublished {result.updated}; skipped {result.skipped} draft work(s).",
        )

    @admin.action(description="Duplicate selected literary works as drafts")
    def duplicate_selected(self, request, queryset):
        works = queryset.prefetch_related("genres", "moods")
        duplicated = [
            EditorialService.duplicate_work(work, actor=request.user) for work in works
        ]
        self.message_user(request, f"Created {len(duplicated)} draft work copy/copies.")


class AlbumTrackInline(TabularInline):
    model = AudioTrack
    fk_name = "album"
    extra = 0
    fields = (
        "track_number",
        "title_ne",
        "narrator",
        "formatted_duration",
        "processing_status",
        "review_status",
        "is_published",
    )
    readonly_fields = fields
    ordering = ("track_number", "chapter_number", "title_ne", "id")
    show_change_link = True

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("narrator")
            .defer(
                "transcript",
                "waveform_data",
                "description_ne",
                "description_en",
                "audio_master_file",
                "stream_file_high",
                "stream_file_low",
            )
        )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Duration")
    def formatted_duration(self, obj):
        return AudioTrackAdmin.format_duration(obj.duration_seconds)


@admin.register(Album)
class AlbumAdmin(CatalogAdminBase):
    inline_track_limit = 50
    play_all_track_limit = 100

    class Media:
        css = {"all": ("admin/css/album-play-all.css",)}
        js = ("admin/js/album-play-all.js",)

    list_display = (
        "cover_thumbnail",
        "title_ne",
        "title_en",
        "author",
        "album_type",
        "track_count",
        "total_duration",
        "is_featured",
        "is_published",
        "release_date",
    )
    list_filter = (
        ("album_type", ChoicesDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("is_featured", BooleanRadioFilter),
        ("is_published", BooleanRadioFilter),
        ("release_date", RangeDateFilter),
    )
    search_alias_mappings = (
        (SearchEntityType.ALBUM, "id"),
        (SearchEntityType.AUTHOR, "author_id"),
    )
    readonly_fields = CatalogAdminBase.readonly_fields + (
        "track_relationship_link",
        "play_all_preview",
        "public_page_preview",
    )
    fieldsets = (
        (
            "Album Information",
            {"fields": ("title_ne", "title_en", "slug", "album_type", "author")},
        ),
        (
            "Description",
            {"fields": ("description_ne", "description_en")},
        ),
        (
            "Classification",
            {"fields": ("genres", "moods", "release_date")},
        ),
        (
            "Artwork",
            {"fields": ("cover_image", "cover_preview")},
        ),
        (
            "Publication",
            {
                "fields": (
                    "is_featured",
                    "is_published",
                    "public_page_preview",
                )
            },
        ),
        (
            "Tracks",
            {"fields": ("track_relationship_link", "play_all_preview")},
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )
    date_hierarchy = "release_date"
    inlines = (AlbumTrackInline,)
    actions = CatalogAdminBase.actions + ("duplicate_selected",)

    def get_urls(self):
        return [
            path(
                "<uuid:object_id>/play-all/<uuid:track_id>/<str:quality>/",
                self.admin_site.admin_view(self.play_all_delivery_view),
                name="catalog_album_play_all_delivery",
            )
        ] + super().get_urls()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "slug", "title_ne", "title_en")
        queryset = queryset.select_related("author").annotate(
            _track_count=Count("audio_tracks", distinct=True),
            _total_duration=Sum("audio_tracks__duration_seconds"),
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer(
                "description_ne",
                "description_en",
                "author__biography_ne",
                "author__biography_en",
                "author__image",
            )
        return queryset

    @admin.display(description="Tracks", ordering="_track_count")
    def track_count(self, obj):
        return obj._track_count

    @admin.display(description="Total duration", ordering="_total_duration")
    def total_duration(self, obj):
        return AudioTrackAdmin.format_duration(obj._total_duration or 0)

    def get_inline_instances(self, request, obj=None):
        track_count = getattr(obj, "_track_count", None)
        if obj is not None and track_count is None:
            track_count = obj.audio_tracks.count()
        if track_count is not None and track_count > self.inline_track_limit:
            return []
        return super().get_inline_instances(request, obj)

    @admin.display(description="Album tracks")
    def track_relationship_link(self, obj):
        if not obj:
            return "Available after the album is saved."
        count = getattr(obj, "_track_count", None)
        if count is None:
            count = obj.audio_tracks.count()
        url = reverse("admin:catalog_audiotrack_changelist")
        return format_html(
            '<a href="{}?album__id__exact={}">Open all {} tracks ↗</a>{}',
            url,
            obj.pk,
            count,
            (
                format_html(
                    " — Inline hidden because this album exceeds the {}-track limit.",
                    self.inline_track_limit,
                )
                if count > self.inline_track_limit
                else ""
            ),
        )

    def _play_all_tracks(self, obj):
        if obj is None or obj.pk is None:
            return [], False
        if hasattr(obj, "_admin_play_all_tracks"):
            return obj._admin_play_all_tracks
        tracks = list(
            AudioTrack.objects.filter(album=obj)
            .filter(Q(stream_file_high__gt="") | Q(stream_file_low__gt=""))
            .select_related("narrator")
            .defer(
                "transcript",
                "waveform_data",
                "description_ne",
                "description_en",
                "audio_master_file",
            )
            .order_by("track_number", "chapter_number", "title_ne", "id")[
                : self.play_all_track_limit + 1
            ]
        )
        truncated = len(tracks) > self.play_all_track_limit
        result = (tracks[: self.play_all_track_limit], truncated)
        obj._admin_play_all_tracks = result
        return result

    @admin.display(description="Play all preview")
    def play_all_preview(self, obj):
        if not obj or not obj.pk:
            return "Available after the album is saved."
        tracks, truncated = self._play_all_tracks(obj)
        manifest = []
        for track in tracks:
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
                                "admin:catalog_album_play_all_delivery",
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
                    "tracks": tracks,
                    "manifest_json": json.dumps(manifest),
                    "truncated": truncated,
                    "limit": self.play_all_track_limit,
                },
            )
        )

    def play_all_delivery_view(self, request, object_id, track_id, quality):
        album = self.get_object(request, object_id)
        if album is None:
            raise Http404
        if not self.has_view_or_change_permission(request, album):
            raise PermissionDenied
        if not request.user.has_perm("catalog.view_audiotrack"):
            raise PermissionDenied
        track = (
            AudioTrack.objects.filter(pk=track_id, album=album)
            .select_related("narrator")
            .first()
        )
        if track is None:
            raise Http404
        try:
            delivery = cloudfront_media_service.deliver(
                track,
                quality=quality,
                request=request,
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

    @admin.display(description="Public page")
    def public_page_preview(self, obj):
        if not obj or not obj.slug:
            return "Available after the album is saved."
        if not obj.is_published:
            return "Available when the album is published."
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Preview public page ↗</a>',
            reverse("catalog:album-detail", kwargs={"slug": obj.slug}),
        )

    def get_view_on_site_url(self, obj=None):
        if obj is None or not obj.is_published:
            return None
        return reverse("catalog:album-detail", kwargs={"slug": obj.slug})

    @admin.action(description="Publish selected albums")
    def publish_selected(self, request, queryset):
        targets = list(queryset.filter(is_published=False))
        result = EditorialService.set_published(
            queryset,
            value=True,
            actor=request.user,
        )
        for album in targets:
            administrative_audit_service.record(
                actor=getattr(request, "user", None),
                action=AdministrativeAuditAction.PUBLISHED,
                obj=album,
                reason="Album published.",
                before={"is_published": False},
                after={"is_published": True},
                request_identifier=getattr(request, "request_identifier", ""),
            )
        self.message_user(request, f"Published {result.updated} album(s).")

    @admin.action(description="Unpublish selected albums")
    def unpublish_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="unpublish_selected",
                title="Unpublish selected albums",
                warning="Selected albums will immediately leave the public catalog.",
                submit_label="Unpublish albums",
            )
        targets = list(queryset.filter(is_published=True))
        result = EditorialService.set_published(
            queryset,
            value=False,
            actor=request.user,
        )
        for album in targets:
            administrative_audit_service.record(
                actor=getattr(request, "user", None),
                action=AdministrativeAuditAction.UNPUBLISHED,
                obj=album,
                reason="Album unpublished.",
                before={"is_published": True},
                after={"is_published": False},
                request_identifier=getattr(request, "request_identifier", ""),
            )
        self.message_user(request, f"Unpublished {result.updated} album(s).")

    @admin.action(description="Duplicate selected albums as drafts")
    def duplicate_selected(self, request, queryset):
        albums = queryset.prefetch_related("genres", "moods")
        duplicated = [
            EditorialService.duplicate_album(album, actor=request.user)
            for album in albums
        ]
        self.message_user(
            request,
            f"Created {len(duplicated)} draft album copy/copies.",
        )


@admin.register(AudioTrack)
class AudioTrackAdmin(
    RomanizedAliasAdminSearchMixin,
    SecureAudioPreviewAdminMixin,
    ProcessingStatusMediaMixin,
    ProtectedDeleteAdminMixin,
    EditorialActionMixin,
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
        "cover_thumbnail",
        "title_ne",
        "work",
        "narrator",
        "album",
        "track_number",
        "formatted_duration",
        "processing_indicator",
        "review_status",
        "publication_indicator",
        "premium_indicator",
        "play_count_cache",
        "published_at",
    )
    list_filter = (
        TrackProcessingStateFilter,
        ("review_status", MultipleChoicesDropdownFilter),
        ("is_published", BooleanRadioFilter),
        ("is_premium", BooleanRadioFilter),
        ("narrator", AutocompleteSelectFilter),
        ("work__author", AutocompleteSelectFilter),
        ("work__category", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
        ("published_at", RangeDateTimeFilter),
        ("duration_seconds", RangeNumericFilter),
    )
    search_fields = (
        "=id",
        "slug",
        "title_ne",
        "title_en",
        "work__title_ne",
        "work__title_en",
        "work__author__name_ne",
        "work__author__name_en",
        "narrator__name_ne",
        "narrator__name_en",
        "album__title_ne",
        "album__title_en",
    )
    search_alias_mappings = (
        (SearchEntityType.TRACK, "id"),
        (SearchEntityType.LITERARY_WORK, "work_id"),
        (SearchEntityType.AUTHOR, "work__author_id"),
        (SearchEntityType.NARRATOR, "narrator_id"),
        (SearchEntityType.ALBUM, "album_id"),
    )
    autocomplete_fields = ("work", "album", "narrator", "language")
    readonly_fields = (
        "id",
        "slug",
        "formatted_duration",
        "processing_indicator",
        "processing_guidance",
        "processing_status",
        "review_status",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "review_comments",
        "waveform_summary",
        "audio_file_availability",
        "audio_file_sizes",
        "audio_quality_summary",
        "audio_preview",
        "cloudfront_preview",
        "publication_readiness",
        "is_featured",
        "is_published",
        "published_at",
        "play_count_cache",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Basic Metadata",
            {
                "fields": (
                    "title_ne",
                    "title_en",
                    "description_ne",
                    "description_en",
                    "slug",
                )
            },
        ),
        (
            "Literary Relationships",
            {
                "fields": (
                    "work",
                    "album",
                    "chapter_number",
                    "track_number",
                    "language",
                )
            },
        ),
        (
            "Narration",
            {"fields": ("narrator", "formatted_duration")},
        ),
        (
            "Audio Files",
            {
                "fields": (
                    "audio_master_file",
                    "stream_file_high",
                    "stream_file_low",
                    "audio_file_availability",
                    "audio_file_sizes",
                    "audio_quality_summary",
                    "audio_preview",
                    "cloudfront_preview",
                )
            },
        ),
        (
            "Spoken Introduction",
            {
                "fields": (
                    "introduction_enabled",
                    "introduction_audio_file",
                    "introduction_duration_seconds",
                    "introduction_notes",
                ),
                "description": (
                    "Optional prepared introduction played before this track in "
                    "playlists, queues, play-all, and automatic transitions. Direct "
                    "playback skips it."
                ),
            },
        ),
        (
            "Transcript",
            {
                "classes": ("collapse",),
                "fields": ("transcript",),
                "description": "Long transcript content is collapsed by default.",
            },
        ),
        (
            "Processing",
            {
                "fields": (
                    "processing_indicator",
                    "processing_status",
                    "processing_guidance",
                    "waveform_summary",
                )
            },
        ),
        (
            "Access and Monetization",
            {"fields": ("is_premium", "is_explicit")},
        ),
        (
            "Publication",
            {
                "fields": (
                    "review_status",
                    "submitted_at",
                    "reviewed_at",
                    "reviewed_by",
                    "review_comments",
                    "publication_readiness",
                    "is_published",
                    "is_featured",
                    "published_at",
                )
            },
        ),
        (
            "Analytics",
            {"fields": ("play_count_cache",)},
        ),
        (
            "System Metadata",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )
    actions = (
        "submit_for_review",
        "approve_selected",
        "request_changes_selected",
        "publish_selected",
        "schedule_selected",
        "reject_selected",
        "archive_selected",
        "retry_processing",
        "feature_selected",
        "unfeature_selected",
        "export_selected_metadata",
    )
    inlines = (TrackReviewEventInline,)
    date_hierarchy = "published_at"
    list_select_related = (
        "work",
        "work__author",
        "album",
        "narrator",
        "language",
        "reviewed_by",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "slug", "title_ne", "title_en")
        queryset = queryset.select_related(
            "work",
            "work__author",
            "album",
            "narrator",
            "language",
            "reviewed_by",
            "processing_job",
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer(
                "description_ne",
                "description_en",
                "transcript",
                "waveform_data",
                "audio_master_file",
                "stream_file_high",
                "stream_file_low",
                "work__description_ne",
                "work__description_en",
                "work__license_notes",
                "work__author__biography_ne",
                "work__author__biography_en",
                "work__author__image",
                "album__description_ne",
                "album__description_en",
                "narrator__biography_ne",
                "narrator__biography_en",
                "narrator__image",
                "language__description",
                "language__image",
                "processing_job__technical_error",
            )
        return queryset

    def save_model(self, request, obj, form, change):
        master_changed = bool(obj.audio_master_file) and (
            not change or "audio_master_file" in form.changed_data
        )
        super().save_model(request, obj, form, change)
        if master_changed:
            queue_audio_processing(obj)

    def get_urls(self):
        return [
            path(
                "scheduled-publications/",
                self.admin_site.admin_view(self.scheduled_publications_view),
                name="catalog_scheduled_publications",
            ),
        ] + super().get_urls()

    def scheduled_publications_view(self, request):
        if not request.user.has_perm("catalog.view_audiotrack"):
            raise PermissionDenied
        if request.method == "POST":
            if not request.user.has_perm("catalog.publish_audiotrack"):
                raise PermissionDenied
            track_id = request.POST.get("track_id")
            action = request.POST.get("publication_action")
            if (
                action in {"cancel", "publish"}
                and request.POST.get("confirmed") != "yes"
            ):
                try:
                    track = (
                        AudioTrack.objects.filter(pk=track_id)
                        .only("id", "title_ne", "review_status")
                        .first()
                    )
                except (ValidationError, ValueError):
                    track = None
                if track is None:
                    self.message_user(
                        request,
                        "Scheduled content no longer exists.",
                        messages.ERROR,
                    )
                    return HttpResponseRedirect(
                        reverse("admin:catalog_scheduled_publications")
                    )
                action_label = (
                    "Cancel schedule" if action == "cancel" else "Publish now"
                )
                return TemplateResponse(
                    request,
                    "admin/catalog/audiotrack/scheduled_action_confirmation.html",
                    {
                        **self.admin_site.each_context(request),
                        "title": action_label,
                        "opts": self.model._meta,
                        "track": track,
                        "publication_action": action,
                        "action_label": action_label,
                    },
                )
            try:
                if action == "reschedule":
                    scheduled_for = parse_datetime(
                        request.POST.get("scheduled_for", "")
                    )
                    if scheduled_for and timezone.is_naive(scheduled_for):
                        scheduled_for = timezone.make_aware(
                            scheduled_for,
                            timezone.get_current_timezone(),
                        )
                    track_review_workflow.reschedule(
                        track_id=track_id,
                        scheduled_for=scheduled_for,
                        actor=request.user,
                    )
                    self.message_user(request, "Publication rescheduled.")
                elif action == "cancel":
                    track_review_workflow.cancel_schedule(
                        track_id=track_id,
                        actor=request.user,
                    )
                    self.message_user(request, "Schedule canceled.")
                elif action == "publish":
                    track_review_workflow.transition(
                        track_id=track_id,
                        target=TrackReviewStatus.PUBLISHED,
                        actor=request.user,
                    )
                    self.message_user(request, "Content published.")
                else:
                    raise ValidationError("Unsupported scheduled-publication action.")
            except (AudioTrack.DoesNotExist, ValidationError) as exc:
                detail = (
                    "; ".join(exc.messages)
                    if isinstance(exc, ValidationError)
                    else "Scheduled content no longer exists."
                )
                self.message_user(request, detail, messages.ERROR)
            return HttpResponseRedirect(reverse("admin:catalog_scheduled_publications"))

        context = {
            **self.admin_site.each_context(request),
            "title": "Scheduled publications",
            "opts": self.model._meta,
            "groups": scheduled_publication_admin_service.get_groups(),
            "configured_timezone": timezone.get_current_timezone_name(),
            "can_publish": request.user.has_perm("catalog.publish_audiotrack"),
        }
        return TemplateResponse(
            request,
            "admin/catalog/audiotrack/scheduled_publications.html",
            context,
        )

    @staticmethod
    def format_duration(seconds):
        seconds = max(0, int(seconds or 0))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @admin.display(description="Duration", ordering="duration_seconds")
    def formatted_duration(self, obj):
        return self.format_duration(obj.duration_seconds)

    @admin.display(description="Processing status", ordering="processing_status")
    def processing_indicator(self, obj):
        return processing_state_badge(track_processing_state(obj))

    @display(
        description="Publication status",
        ordering="is_published",
        label={"published": "success", "draft": "info"},
    )
    def publication_indicator(self, obj):
        return ("published", "Published") if obj.is_published else ("draft", "Draft")

    @display(
        description="Premium",
        ordering="is_premium",
        label={"premium": "warning", "free": "info"},
    )
    def premium_indicator(self, obj):
        return ("premium", "Premium") if obj.is_premium else ("free", "Free")

    @admin.display(description="Cover")
    def cover_thumbnail(self, obj):
        image = obj.work.cover_image
        if not image:
            return "—"
        try:
            url = image.url
        except (ValueError, AttributeError):
            return "—"
        return format_html(
            '<img src="{}" alt="" loading="lazy" decoding="async" '
            'style="height:44px;width:44px;'
            'object-fit:cover;border-radius:8px;">',
            url,
        )

    @admin.display(description="Audio files")
    def audio_file_availability(self, obj):
        states = (
            ("Master", bool(obj.audio_master_file)),
            ("High", bool(obj.stream_file_high)),
            ("Low", bool(obj.stream_file_low)),
        )
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:2px 8px;'
            'border-radius:999px;margin-right:4px;background:{};color:white">'
            "{}</span>",
            (
                (
                    "#15803d" if available else "#71717a",
                    f"{label}: {'available' if available else 'missing'}",
                )
                for label, available in states
            ),
        )

    @staticmethod
    def _format_file_size(file_field):
        if not file_field:
            return "missing"
        try:
            size = file_field.size
        except (AttributeError, NotImplementedError, OSError, ValueError, ClientError):
            return "unavailable"
        units = ("B", "KB", "MB", "GB")
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return "unavailable"

    @admin.display(description="File sizes")
    def audio_file_sizes(self, obj):
        return (
            f"Master: {self._format_file_size(obj.audio_master_file)} · "
            f"High: {self._format_file_size(obj.stream_file_high)} · "
            f"Low: {self._format_file_size(obj.stream_file_low)}"
        )

    @admin.display(description="Audio quality")
    def audio_quality_summary(self, obj):
        qualities = ["Original master"] if obj.audio_master_file else []
        if obj.stream_file_high:
            qualities.append("High")
        if obj.stream_file_low:
            qualities.append("Low")
        return ", ".join(qualities) or "No audio renditions available."

    @admin.display(description="Waveform")
    def waveform_summary(self, obj):
        sample_count = (
            len(obj.waveform_data) if isinstance(obj.waveform_data, list) else 0
        )
        return (
            f"{sample_count:,} waveform samples stored; JSON is hidden from this form."
            if sample_count
            else "No waveform samples stored. Full JSON is hidden from this form."
        )

    @admin.display(description="Processing diagnostics")
    def processing_guidance(self, obj):
        if obj.processing_status == TrackProcessingStatus.FAILED:
            return (
                "Processing failed. This schema does not persist a detailed error "
                "message; inspect worker logs, then use Retry processing."
            )
        if obj.processing_status == TrackProcessingStatus.PROCESSING:
            return "Audio processing is currently in progress."
        if obj.processing_status == TrackProcessingStatus.PENDING:
            return "Audio is waiting in the processing queue."
        return "Processing is complete and the track is eligible for review."

    @display(
        description="Publishing readiness",
        label={
            "ready": "success",
            "blocked": "danger",
            "published": "info",
        },
    )
    def publication_readiness(self, obj):
        if obj.is_published:
            return ("published", "Already published")
        if obj.processing_status != TrackProcessingStatus.READY:
            return ("blocked", "Blocked: audio processing is not ready")
        if obj.review_status != TrackReviewStatus.APPROVED:
            return ("blocked", "Blocked: editorial approval is required")
        return ("ready", "Ready to publish")

    @admin.display(description="Safe audio preview")
    def audio_preview(self, obj):
        return self.render_audio_preview(obj)

    @admin.display(description="CloudFront access")
    def cloudfront_preview(self, obj):
        if not (obj.stream_file_high or obj.stream_file_low):
            return "Unavailable until a processed rendition exists."
        return (
            "Preview links use the permission-checked CloudFront delivery service. "
            "Private and premium media receive short-lived signed URLs."
        )

    def get_audio_preview_sources(self, obj):
        return [
            {
                "quality": "low",
                "label": "Low quality",
                "available": bool(obj.stream_file_low),
            },
            {
                "quality": "high",
                "label": "High quality",
                "available": bool(obj.stream_file_high),
            },
        ]

    def get_audio_preview_title(self, obj):
        return f"{obj.title_ne} — {obj.narrator.name_ne}"

    def get_audio_preview_duration(self, obj):
        return obj.duration_seconds

    def resolve_audio_delivery(self, obj, *, quality, request):
        return cloudfront_media_service.deliver(
            obj,
            quality=quality,
            request=request,
        )

    @action(
        description="Submit selected for review",
        icon="rate_review",
        permissions=("change",),
    )
    def submit_for_review(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="submit_for_review",
                title="Submit tracks for editorial review",
                warning="Every selected track will be validated before submission.",
                submit_label="Submit for review",
            )
        report = track_review_workflow.transition_many_detailed(
            queryset=queryset,
            target=TrackReviewStatus.SUBMITTED,
            actor=request.user,
        )
        report_bulk_action(self, request, verb="Submitted", report=report)

    @action(
        description="Approve selected",
        icon="approval",
        permissions=("approve",),
        variant=ActionVariant.SUCCESS,
    )
    def approve_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="approve_selected",
                title="Approve selected tracks",
                warning="Approval is recorded in the editorial audit trail.",
                submit_label="Approve tracks",
            )
        report = track_review_workflow.transition_many_detailed(
            queryset=queryset,
            target=TrackReviewStatus.APPROVED,
            actor=request.user,
        )
        report_bulk_action(self, request, verb="Approved", report=report)

    @action(
        description="Publish selected",
        icon="publish",
        permissions=("publish",),
        variant=ActionVariant.SUCCESS,
    )
    def publish_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="publish_selected",
                title="Publish selected tracks",
                warning=(
                    "Only approved, processing-ready tracks with resolved rights "
                    "will be published."
                ),
                submit_label="Publish tracks",
            )
        report = track_review_workflow.transition_many_detailed(
            queryset=queryset,
            target=TrackReviewStatus.PUBLISHED,
            actor=request.user,
        )
        report_bulk_action(self, request, verb="Published", report=report)

    @admin.action(description="Request changes for selected submissions")
    def request_changes_selected(self, request, queryset):
        return self._reasoned_transition(
            request,
            queryset,
            target=TrackReviewStatus.CHANGES_REQUESTED,
            action_name="request_changes_selected",
            title="Request editorial changes",
        )

    @admin.action(description="Reject selected submitted tracks")
    def reject_selected(self, request, queryset):
        return self._reasoned_transition(
            request,
            queryset,
            target=TrackReviewStatus.REJECTED,
            action_name="reject_selected",
            title="Reject submissions",
        )

    @admin.action(description="Schedule selected approved tracks")
    def schedule_selected(self, request, queryset):
        if "confirm_workflow" not in request.POST:
            return self._workflow_confirmation(
                request,
                queryset,
                form=ReviewScheduleForm(),
                action_name="schedule_selected",
                title="Schedule publication",
            )
        form = ReviewScheduleForm(request.POST)
        if not form.is_valid():
            return self._workflow_confirmation(
                request,
                queryset,
                form=form,
                action_name="schedule_selected",
                title="Schedule publication",
            )
        result = track_review_workflow.transition_many(
            queryset=queryset,
            target=TrackReviewStatus.SCHEDULED,
            actor=request.user,
            comment=form.cleaned_data["comment"],
            scheduled_for=form.cleaned_data["scheduled_for"],
        )
        self.message_user(
            request,
            f"Scheduled {result.updated}; skipped {result.skipped} track(s).",
        )

    @action(
        description="Archive selected",
        icon="archive",
        permissions=("publish",),
        variant=ActionVariant.WARNING,
    )
    def archive_selected(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="archive_selected",
                title="Archive selected tracks",
                warning="Published tracks will immediately leave the public catalog.",
                submit_label="Archive tracks",
            )
        report = track_review_workflow.transition_many_detailed(
            queryset=queryset,
            target=TrackReviewStatus.ARCHIVED,
            actor=request.user,
        )
        report_bulk_action(self, request, verb="Archived", report=report)

    def _reasoned_transition(
        self,
        request,
        queryset,
        *,
        target,
        action_name,
        title,
    ):
        if "confirm_workflow" not in request.POST:
            return self._workflow_confirmation(
                request,
                queryset,
                form=ReviewReasonForm(),
                action_name=action_name,
                title=title,
            )
        form = ReviewReasonForm(request.POST)
        if not form.is_valid():
            return self._workflow_confirmation(
                request,
                queryset,
                form=form,
                action_name=action_name,
                title=title,
            )
        result = track_review_workflow.transition_many(
            queryset=queryset,
            target=target,
            actor=request.user,
            comment=form.cleaned_data["reason"],
        )
        self.message_user(
            request,
            f"Updated {result.updated}; skipped {result.skipped} track(s).",
        )

    def _workflow_confirmation(
        self,
        request,
        queryset,
        *,
        form,
        action_name,
        title,
    ):
        return TemplateResponse(
            request,
            "admin/catalog/audiotrack/review_confirmation.html",
            {
                **self.admin_site.each_context(request),
                "title": title,
                "form": form,
                "queryset": queryset,
                "action_name": action_name,
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("catalog.approve_audiotrack"):
            for name in (
                "approve_selected",
                "request_changes_selected",
                "reject_selected",
            ):
                actions.pop(name, None)
        if not request.user.has_perm("catalog.publish_audiotrack"):
            for name in ("schedule_selected", "publish_selected", "archive_selected"):
                actions.pop(name, None)
        return actions

    def has_approve_permission(self, request):
        return request.user.has_perm("catalog.approve_audiotrack")

    def has_publish_permission(self, request):
        return request.user.has_perm("catalog.publish_audiotrack")

    @admin.action(description="Unpublish selected tracks")
    def unpublish_selected(self, request, queryset):
        result = track_review_workflow.transition_many(
            queryset=queryset,
            target=TrackReviewStatus.ARCHIVED,
            actor=request.user,
        )
        self.message_user(
            request,
            f"Archived {result.updated}; skipped {result.skipped} track(s).",
        )

    @action(
        description="Retry selected failed tracks",
        icon="restart_alt",
        permissions=("retry",),
        variant=ActionVariant.WARNING,
    )
    def retry_processing(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="retry_processing",
                title="Retry failed audio processing",
                warning="Only failed tracks without an active job can be queued.",
                submit_label="Queue retries",
            )

        def retry(track):
            result = EditorialService.retry_processing(
                queryset.model._base_manager.filter(pk=track.pk),
                actor=request.user,
            )
            if result.updated != 1:
                raise ValidationError(
                    "Track is not failed, has an active job, or exhausted retries."
                )

        report = run_object_action(
            model_admin=self,
            request=request,
            queryset=queryset,
            operation=retry,
        )
        report_bulk_action(self, request, verb="Queued", report=report)

    def has_retry_permission(self, request):
        return request.user.has_perm("catalog.retry_audioprocessingjob")

    @action(
        description="Export selected metadata",
        icon="download",
        permissions=("view",),
    )
    def export_selected_metadata(self, request, queryset):
        permitted = []
        for track in queryset:
            if not self.has_view_permission(request, track):
                raise PermissionDenied(f"You cannot export metadata for {track}.")
            permitted.append(track.pk)
        return export_metadata_csv(
            queryset=queryset.filter(pk__in=permitted),
            fields=(
                "id",
                "slug",
                "title_ne",
                "title_en",
                "processing_status",
                "review_status",
                "is_published",
                "is_featured",
                "is_premium",
                "duration_seconds",
                "published_at",
            ),
            filename="sunnekatha-track-metadata.csv",
        )


@admin.register(PendingReviewTrack)
class PendingReviewTrackAdmin(ProcessingStatusMediaMixin, ModelAdmin):
    list_display = (
        "content_title",
        "category_display",
        "creator_or_uploader",
        "author",
        "narrator",
        "submitted_at",
        "processing_indicator",
        "copyright_status",
        "assigned_reviewer",
        "review_age",
        "attention_flags",
        "open_review_page",
    )
    list_display_links = None
    list_filter = (
        ("work__category", AutocompleteSelectFilter),
        PendingCreatorFilter,
        ("reviewed_by", AutocompleteSelectFilter),
        ("processing_status", ChoicesDropdownFilter),
        ("work__copyright_status", ChoicesDropdownFilter),
        ("submitted_at", RangeDateTimeFilter),
    )
    search_fields = (
        "title_ne",
        "title_en",
        "work__title_ne",
        "work__title_en",
    )
    actions = (
        "assign_reviewer",
        "approve_safe_selected",
        "request_changes_selected",
    )
    ordering = ("submitted_at", "id")
    list_per_page = 50

    def get_queryset(self, request):
        contributor_queryset = ContentContributor.objects.select_related(
            "creator__user"
        ).order_by("created_at", "id")
        return (
            super()
            .get_queryset(request)
            .filter(review_status=TrackReviewStatus.SUBMITTED)
            .select_related(
                "work__author",
                "narrator__user",
                "language",
                "reviewed_by",
                "processing_job__upload_session__user",
            )
            .prefetch_related(
                Prefetch(
                    "contributors",
                    queryset=contributor_queryset,
                    to_attr="_pending_review_contributors",
                )
            )
            .defer(
                "transcript",
                "waveform_data",
                "description_ne",
                "description_en",
                "audio_master_file",
                "stream_file_high",
                "stream_file_low",
                "work__description_ne",
                "work__description_en",
            )
        )

    def has_module_permission(self, request):
        return request.user.has_perm("catalog.approve_audiotrack")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("catalog.approve_audiotrack")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("catalog.approve_audiotrack")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Content title", ordering="title_ne")
    def content_title(self, obj):
        return obj.title_ne

    @admin.display(description="Category", ordering="work__category__name_ne")
    def category_display(self, obj):
        return obj.work.category

    @admin.display(description="Creator / uploader")
    def creator_or_uploader(self, obj):
        job = getattr(obj, "processing_job", None)
        if job and job.upload_session_id:
            return job.upload_session.user
        contributors = getattr(obj, "_pending_review_contributors", ())
        if contributors:
            return contributors[0].creator.user
        return obj.narrator.user or "—"

    @admin.display(description="Author", ordering="work__author__name_ne")
    def author(self, obj):
        return obj.work.author

    @admin.display(description="Processing", ordering="processing_status")
    def processing_indicator(self, obj):
        return processing_state_badge(track_processing_state(obj))

    @admin.display(description="Copyright", ordering="work__copyright_status")
    def copyright_status(self, obj):
        return obj.work.get_copyright_status_display()

    @admin.display(description="Assigned reviewer", ordering="reviewed_by")
    def assigned_reviewer(self, obj):
        return obj.reviewed_by or "Unassigned"

    @admin.display(description="Review age", ordering="submitted_at")
    def review_age(self, obj):
        if not obj.submitted_at:
            return "Unknown"
        elapsed = timezone.now() - obj.submitted_at
        if elapsed.days:
            return f"{elapsed.days}d {elapsed.seconds // 3600}h"
        return f"{elapsed.seconds // 3600}h {(elapsed.seconds % 3600) // 60}m"

    @admin.display(description="Attention")
    def attention_flags(self, obj):
        issues = review_attention_issues(obj)
        if not issues:
            return format_html(
                '<span style="color:#15803d;font-weight:600">Ready for review</span>'
            )
        return format_html_join(
            " ",
            '<span style="display:inline-block;background:#9a3412;color:white;'
            'padding:2px 7px;border-radius:999px;margin:1px">{}</span>',
            ((issue,) for issue in issues),
        )

    @admin.display(description="Review")
    def open_review_page(self, obj):
        url = reverse("admin:catalog_audiotrack_change", args=(obj.pk,))
        return format_html('<a href="{}">Open review page ↗</a>', url)

    @action(
        description="Assign reviewer",
        icon="assignment_ind",
        permissions=("change",),
    )
    def assign_reviewer(self, request, queryset):
        if "confirm_workflow" not in request.POST:
            return self._confirmation(
                request,
                queryset,
                form=AssignReviewerForm(),
                action_name="assign_reviewer",
                title="Assign reviewer",
            )
        form = AssignReviewerForm(request.POST)
        if not form.is_valid():
            return self._confirmation(
                request,
                queryset,
                form=form,
                action_name="assign_reviewer",
                title="Assign reviewer",
            )
        report = pending_review_service.assign_reviewer_detailed(
            queryset=queryset,
            reviewer=form.cleaned_data["reviewer"],
            actor=request.user,
        )
        report_bulk_action(self, request, verb="Assigned", report=report)

    @admin.action(description="Approve selected items that pass readiness checks")
    def approve_safe_selected(self, request, queryset):
        result = pending_review_service.approve_safe(
            queryset=queryset,
            actor=request.user,
        )
        self.message_user(
            request,
            f"Approved {result.updated}; skipped {result.skipped} item(s) with "
            "audio that is not processing-ready.",
        )

    @admin.action(description="Request changes")
    def request_changes_selected(self, request, queryset):
        if "confirm_workflow" not in request.POST:
            return self._confirmation(
                request,
                queryset,
                form=ReviewReasonForm(),
                action_name="request_changes_selected",
                title="Request editorial changes",
            )
        form = ReviewReasonForm(request.POST)
        if not form.is_valid():
            return self._confirmation(
                request,
                queryset,
                form=form,
                action_name="request_changes_selected",
                title="Request editorial changes",
            )
        result = track_review_workflow.transition_many(
            queryset=queryset,
            target=TrackReviewStatus.CHANGES_REQUESTED,
            actor=request.user,
            comment=form.cleaned_data["reason"],
        )
        self.message_user(
            request,
            f"Requested changes for {result.updated}; skipped "
            f"{result.skipped} item(s).",
        )

    def _confirmation(
        self,
        request,
        queryset,
        *,
        form,
        action_name,
        title,
    ):
        return TemplateResponse(
            request,
            "admin/catalog/audiotrack/review_confirmation.html",
            {
                **self.admin_site.each_context(request),
                "title": title,
                "form": form,
                "queryset": queryset,
                "action_name": action_name,
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )


class ProcessingJobStateFilter(admin.SimpleListFilter):
    title = "processing state"
    parameter_name = "processing_state"

    def lookups(self, request, model_admin):
        return ProcessingState.CHOICES

    def queryset(self, request, queryset):
        state = self.value()
        if state == ProcessingState.PUBLISHED:
            return queryset.filter(track__is_published=True)
        if state in {
            ProcessingState.QUEUED,
            ProcessingState.PROCESSING,
            ProcessingState.READY,
            ProcessingState.FAILED,
        }:
            return queryset.filter(track__is_published=False, status=state)
        if state in {ProcessingState.DRAFT, ProcessingState.UPLOADED}:
            return queryset.none()
        return queryset


@admin.register(AudioProcessingJob)
class AudioProcessingJobAdmin(
    ProtectedDeleteAdminMixin,
    ProcessingStatusMediaMixin,
    ModelAdmin,
):
    list_display = (
        "status_badge",
        "track_link",
        "upload_link",
        "stage",
        "error_summary",
        "attempts_display",
        "last_attempt_at",
        "retry_display",
    )
    list_filter = (
        ProcessingJobStateFilter,
        ("stage", ChoicesDropdownFilter),
        ("attempts", RangeNumericFilter),
        ("last_attempt_at", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "=track__id",
        "track__slug",
        "track__title_ne",
        "track__title_en",
        "track__work__author__name_ne",
        "track__work__author__name_en",
        "track__narrator__name_ne",
        "track__narrator__name_en",
        "upload_session__original_filename",
        "error_summary",
    )
    list_select_related = ("track", "upload_session")
    actions = ()
    readonly_fields = (
        "id",
        "status_badge",
        "track_link",
        "upload_link",
        "stage",
        "error_summary",
        "attempts_display",
        "last_attempt_at",
        "retry_display",
        "created_at",
        "updated_at",
        "technical_error",
        "retry_initiated_by",
        "retry_requested_at",
    )

    def has_retry_permission(self, request):
        return request.user.has_perm("catalog.retry_audioprocessingjob")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "failed/",
                self.admin_site.admin_view(self.failed_jobs_view),
                name="catalog_audioprocessingjob_failed",
            ),
            path(
                "failed/<uuid:object_id>/retry/",
                self.admin_site.admin_view(self.retry_failed_job_view),
                name="catalog_audioprocessingjob_retry",
            ),
        ]
        return custom_urls + urls

    def _failed_queryset(self):
        return (
            AudioProcessingJob.objects.filter(status=AudioProcessingJobStatus.FAILED)
            .select_related(
                "track",
                "track__narrator",
                "upload_session",
                "upload_session__user",
                "retry_initiated_by",
            )
            .defer(
                "technical_error",
                "track__transcript",
                "track__waveform_data",
                "track__description_ne",
                "track__description_en",
            )
        )

    def _apply_failed_filters(self, request, queryset):
        if stage := request.GET.get("stage"):
            queryset = queryset.filter(stage=stage)
        if created_date := parse_date(request.GET.get("date", "")):
            queryset = queryset.filter(created_at__date=created_date)
        if creator := request.GET.get("creator"):
            queryset = queryset.filter(upload_session__user_id=creator)
        if query := request.GET.get("q", "").strip():
            queryset = queryset.filter(
                Q(track__title_ne__icontains=query)
                | Q(track__title_en__icontains=query)
                | Q(upload_session__original_filename__icontains=query)
            )
        return queryset

    def failed_jobs_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        queryset = self._apply_failed_filters(request, self._failed_queryset())
        selected_ids = request.POST.getlist("_selected_action")
        if request.method == "POST":
            if not self.has_retry_permission(request):
                raise PermissionDenied
            selected = queryset.filter(pk__in=selected_ids)
            if request.POST.get("confirm") == "yes":
                result = EditorialService.retry_processing(
                    AudioTrack.objects.filter(processing_job__in=selected),
                    actor=request.user,
                )
                self.message_user(
                    request,
                    f"Queued {result.updated} job(s); skipped "
                    f"{result.skipped} unavailable or active job(s).",
                    messages.SUCCESS if result.updated else messages.WARNING,
                )
                return HttpResponseRedirect(
                    reverse("admin:catalog_audioprocessingjob_failed")
                )
            if selected.exists():
                context = {
                    **self.admin_site.each_context(request),
                    "title": "Confirm processing retries",
                    "opts": self.model._meta,
                    "jobs": selected,
                    "selected_ids": selected_ids,
                    "return_url": reverse("admin:catalog_audioprocessingjob_failed"),
                }
                return TemplateResponse(
                    request,
                    "admin/catalog/audioprocessingjob/retry_confirmation.html",
                    context,
                )
            self.message_user(
                request, "Select at least one failed job.", messages.WARNING
            )

        paginator = Paginator(queryset, 50)
        page = paginator.get_page(request.GET.get("page"))
        creators = (
            self._failed_queryset()
            .exclude(upload_session__user=None)
            .values_list(
                "upload_session__user_id",
                "upload_session__user__display_name",
                "upload_session__user__email",
            )
            .distinct()
            .order_by("upload_session__user__display_name")
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "Failed audio processing",
            "opts": self.model._meta,
            "page": page,
            "stages": AudioProcessingStage.choices,
            "creators": creators,
            "filters": request.GET,
            "can_retry": self.has_retry_permission(request),
        }
        return TemplateResponse(
            request,
            "admin/catalog/audioprocessingjob/failed_jobs.html",
            context,
        )

    def retry_failed_job_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseRedirect(
                reverse("admin:catalog_audioprocessingjob_failed")
            )
        if not self.has_retry_permission(request):
            raise PermissionDenied
        job = self._failed_queryset().filter(pk=object_id).first()
        if job is None:
            self.message_user(
                request,
                "That job is no longer failed or available for retry.",
                messages.WARNING,
            )
        else:
            result = EditorialService.retry_processing(
                AudioTrack.objects.filter(pk=job.track_id),
                actor=request.user,
            )
            self.message_user(
                request,
                "Retry queued." if result.updated else "Job is already active.",
                messages.SUCCESS if result.updated else messages.WARNING,
            )
        return HttpResponseRedirect(reverse("admin:catalog_audioprocessingjob_failed"))

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                "Processing status",
                {
                    "fields": (
                        "status_badge",
                        "stage",
                        "error_summary",
                        "attempts_display",
                        "last_attempt_at",
                        "retry_display",
                        "retry_initiated_by",
                        "retry_requested_at",
                    )
                },
            ),
            (
                "Related records",
                {"fields": ("track_link", "upload_link")},
            ),
            (
                "System metadata",
                {
                    "classes": ("collapse",),
                    "fields": ("id", "created_at", "updated_at"),
                },
            ),
        ]
        if request.user.is_superuser:
            fieldsets.append(
                (
                    "Technical information — superusers only",
                    {
                        "classes": ("collapse",),
                        "fields": ("technical_error",),
                    },
                )
            )
        return tuple(fieldsets)

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return processing_state_badge(obj.admin_processing_state)

    @admin.display(description="Related track", ordering="track__title_ne")
    def track_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:catalog_audiotrack_change", args=(obj.track_id,)),
            obj.track,
        )

    @admin.display(description="Related upload")
    def upload_link(self, obj):
        if obj.upload_session_id is None:
            return "—"
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                "admin:uploads_uploadsession_change",
                args=(obj.upload_session_id,),
            ),
            obj.upload_session,
        )

    @admin.display(description="Attempts", ordering="attempts")
    def attempts_display(self, obj):
        return f"{obj.attempts} / {obj.max_attempts}"

    @display(description="Retry available", boolean=True)
    def retry_display(self, obj):
        return obj.retry_available
