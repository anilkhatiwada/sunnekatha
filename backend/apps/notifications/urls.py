from django.urls import path

from apps.notifications.views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationListView,
    UnreadNotificationCountView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("unread-count/", UnreadNotificationCountView.as_view(), name="unread-count"),
    path(
        "read-all/",
        MarkAllNotificationsReadView.as_view(),
        name="mark-all-read",
    ),
    path(
        "<uuid:notification_id>/read/",
        MarkNotificationReadView.as_view(),
        name="mark-read",
    ),
]
