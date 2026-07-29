import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification, NotificationType

pytestmark = pytest.mark.django_db


def create_notification(user, *, is_read=False, title="नयाँ सूचना"):
    return Notification.objects.create(
        recipient=user,
        notification_type=NotificationType.PLAYLIST_UPDATED,
        title=title,
        read_at=timezone.now() if is_read else None,
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_notification_endpoints_require_authentication():
    client = APIClient()

    assert (
        client.get(reverse("notifications:list")).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.get(reverse("notifications:unread-count")).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.post(reverse("notifications:mark-all-read")).status_code
        == status.HTTP_401_UNAUTHORIZED
    )


def test_list_returns_only_current_users_notifications_and_supports_unread_filter():
    user = UserFactory()
    other_user = UserFactory()
    unread = create_notification(user, title="नपढिएको")
    create_notification(user, is_read=True, title="पढिएको")
    create_notification(other_user, title="अर्को प्रयोगकर्ता")

    response = authenticated_client(user).get(
        reverse("notifications:list"),
        {"unread": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(unread.id)
    assert response.data["results"][0]["isRead"] is False


def test_unread_count_is_scoped_to_current_user():
    user = UserFactory()
    other_user = UserFactory()
    create_notification(user)
    create_notification(user, is_read=True)
    create_notification(other_user)

    response = authenticated_client(user).get(reverse("notifications:unread-count"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"unreadCount": 1}


def test_mark_read_is_idempotent_and_cannot_access_another_users_notification():
    user = UserFactory()
    other_user = UserFactory()
    notification = create_notification(user)
    other_notification = create_notification(other_user)
    client = authenticated_client(user)
    url = reverse("notifications:mark-read", args=[notification.id])

    first = client.post(url)
    first_read_at = first.data["readAt"]
    second = client.patch(url)

    assert first.status_code == status.HTTP_200_OK
    assert first.data["isRead"] is True
    assert second.status_code == status.HTTP_200_OK
    assert second.data["readAt"] == first_read_at
    assert (
        client.post(
            reverse("notifications:mark-read", args=[other_notification.id])
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_mark_all_read_updates_only_current_users_unread_notifications():
    user = UserFactory()
    other_user = UserFactory()
    create_notification(user)
    create_notification(user)
    other_notification = create_notification(other_user)

    response = authenticated_client(user).post(reverse("notifications:mark-all-read"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"updatedCount": 2, "unreadCount": 0}
    assert not Notification.objects.filter(recipient=user, read_at=None).exists()
    other_notification.refresh_from_db()
    assert other_notification.read_at is None
