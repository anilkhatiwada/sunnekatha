from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.search.models import SearchAlias


@admin.register(SearchAlias)
class SearchAliasAdmin(ModelAdmin):
    list_display = ("alias", "entity_type", "object_id", "updated_at")
    list_filter = ("entity_type",)
    search_fields = ("alias", "normalized_alias", "object_id")
    readonly_fields = ("normalized_alias", "created_at", "updated_at")
