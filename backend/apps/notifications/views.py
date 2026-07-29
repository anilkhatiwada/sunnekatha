from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        queryset = Notification.objects.filter(recipient=self.request.user)
        unread = self.request.query_params.get("unread")
        if unread == "true":
            queryset = queryset.filter(read_at__isnull=True)
        elif unread == "false":
            queryset = queryset.filter(read_at__isnull=False)
        return queryset.order_by("-created_at", "-id")


class UnreadNotificationCountView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = NotificationSerializer

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()
        return Response({"unreadCount": count})


class MarkNotificationReadView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = NotificationSerializer

    def mark(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient=request.user,
        )
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at", "updated_at"))
        return Response(self.get_serializer(notification).data)

    post = mark
    patch = mark


class MarkAllNotificationsReadView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = NotificationSerializer

    def post(self, request):
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).update(read_at=now, updated_at=now)
        return Response({"updatedCount": updated, "unreadCount": 0})
