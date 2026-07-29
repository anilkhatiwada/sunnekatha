from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.creators.models import ContentContributor, CreatorProfile, RightsLicenseAudit


@admin.register(CreatorProfile)
class CreatorProfileAdmin(ModelAdmin):
    list_display = ("display_name", "user", "is_approved", "roles")
    list_filter = ("is_approved",)
    search_fields = ("display_name", "user__email")
    autocomplete_fields = ("user",)


@admin.register(ContentContributor)
class ContentContributorAdmin(ModelAdmin):
    list_display = ("track", "creator", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("track__title_ne", "creator__display_name")
    autocomplete_fields = ("track", "creator")


@admin.register(RightsLicenseAudit)
class RightsLicenseAuditAdmin(ModelAdmin):
    list_display = ("track", "actor", "created_at")
    search_fields = ("track__title_ne", "actor__email")
    readonly_fields = ("track", "actor", "changes", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
