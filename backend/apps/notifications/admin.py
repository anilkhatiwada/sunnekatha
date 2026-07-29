from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.common.admin import ProtectedDeleteAdminMixin
from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "recipient",
        "notification_type",
        "title",
        "read_at",
        "created_at",
    )
    list_filter = ("notification_type", "read_at", "created_at")
    search_fields = ("recipient__email", "title", "message", "deduplication_key")
    list_select_related = ("recipient",)
    readonly_fields = (
        "id",
        "recipient",
        "notification_type",
        "title",
        "message",
        "data",
        "action_url",
        "read_at",
        "deduplication_key",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
