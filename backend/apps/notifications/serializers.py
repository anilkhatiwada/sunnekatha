from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="notification_type")
    actionUrl = serializers.CharField(source="action_url")
    isRead = serializers.SerializerMethodField()
    readAt = serializers.DateTimeField(source="read_at")
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "message",
            "data",
            "actionUrl",
            "isRead",
            "readAt",
            "createdAt",
        )
        read_only_fields = fields

    def get_isRead(self, obj) -> bool:
        return obj.read_at is not None
