from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.common.models import AdministrativeAudit, AdministrativeAuditAction


class ProtectedDeleteAdminMixin:
    """Keep durable editorial records out of Django's destructive delete flow."""

    def save_model(self, request, obj, form, change):
        from apps.common.audit import administrative_audit_service

        changed_fields = tuple(getattr(form, "changed_data", ()) or ())
        before = {
            field: getattr(form, "initial", {}).get(field) for field in changed_fields
        }
        super().save_model(request, obj, form, change)
        after = {field: getattr(obj, field, None) for field in changed_fields}
        administrative_audit_service.record(
            actor=request.user,
            action=(
                AdministrativeAuditAction.EDITED
                if change
                else AdministrativeAuditAction.CREATED
            ),
            obj=obj,
            reason=(
                f"Changed fields: {', '.join(changed_fields)}" if changed_fields else ""
            ),
            before=before,
            after=after,
            request_identifier=getattr(request, "request_identifier", ""),
        )

    def has_delete_permission(self, request, obj=None):
        return False


class ServiceManagedFeaturedAdminMixin:
    """Allow form edits while keeping featured mutations in the service layer."""

    def save_model(self, request, obj, form, change):
        changed = "is_featured" in (getattr(form, "changed_data", ()) or ())
        desired = bool(getattr(obj, "is_featured", False))
        if changed and change:
            previous = type(obj)._base_manager.only("is_featured").get(pk=obj.pk)
            obj.is_featured = previous.is_featured
        super().save_model(request, obj, form, change)
        if changed:
            from apps.catalog.services import EditorialService

            EditorialService.set_featured(
                type(obj)._base_manager.filter(pk=obj.pk),
                value=desired,
                actor=request.user,
            )
            obj.is_featured = desired


class ImagePreviewAdminMixin:
    image_field_name = "image"

    def _image(self, obj, *, height):
        image = getattr(obj, self.image_field_name, None)
        if not image:
            return "—"
        try:
            url = image.url
        except (ValueError, AttributeError):
            return "—"
        return format_html(
            '<img src="{}" alt="" loading="lazy" decoding="async" '
            'style="height:{}px;max-width:240px;'
            'object-fit:cover;border-radius:8px;">',
            url,
            height,
        )

    @admin.display(description="Image")
    def image_thumbnail(self, obj):
        return self._image(obj, height=40)

    @admin.display(description="Current image")
    def image_preview(self, obj):
        return self._image(obj, height=160)


class CoverPreviewAdminMixin(ImagePreviewAdminMixin):
    image_field_name = "cover_image"

    @admin.display(description="Cover")
    def cover_thumbnail(self, obj):
        return self._image(obj, height=44)

    @admin.display(description="Current cover")
    def cover_preview(self, obj):
        return self._image(obj, height=180)


@admin.register(AdministrativeAudit)
class AdministrativeAuditAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "staff_user",
        "action",
        "object_type",
        "object_repr",
        "reason",
        "request_identifier",
    )
    list_filter = ("action", "object_type", "staff_user", "created_at")
    search_fields = (
        "object_repr",
        "object_type",
        "object_id",
        "staff_user__email",
        "reason",
        "request_identifier",
    )
    list_select_related = ("staff_user",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "staff_user",
        "action",
        "object_type",
        "object_id",
        "object_repr",
        "reason",
        "before_summary",
        "after_summary",
        "request_identifier",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
