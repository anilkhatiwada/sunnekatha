from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.common.admin import ImagePreviewAdminMixin, ProtectedDeleteAdminMixin
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood


class TaxonomyAdmin(ProtectedDeleteAdminMixin, ImagePreviewAdminMixin, ModelAdmin):
    list_display = (
        "name_ne",
        "name_en",
        "slug",
        "sort_order",
        "is_active",
        "image_thumbnail",
        "updated_at",
    )
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_ne", "name_en", "slug", "description")
    readonly_fields = ("id", "slug", "image_preview", "created_at", "updated_at")
    fields = (
        "id",
        "slug",
        "name_ne",
        "name_en",
        "description",
        "image",
        "image_preview",
        "sort_order",
        "is_active",
        "created_at",
        "updated_at",
    )
    ordering = ("sort_order", "name_ne")


admin.site.register(Genre, TaxonomyAdmin)
admin.site.register(Mood, TaxonomyAdmin)
admin.site.register(Language, TaxonomyAdmin)
admin.site.register(ContentCategory, TaxonomyAdmin)
