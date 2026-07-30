import { apiClient } from "@/services/api-client";
import { unwrapPage } from "@/services/public-api-utils";
import type {
  ApiNotification,
  ApiNotificationPage,
  ApiUnreadNotificationCount,
} from "@/types";

export function getNotifications() {
  return apiClient
    .get<ApiNotificationPage>("/notifications/", {
      query: { pageSize: 50 },
      requiresAuth: true,
    })
    .then(unwrapPage)
    .then((items) => items.map(sanitizeNotification));
}

function sanitizeNotification(notification: ApiNotification): ApiNotification {
  return {
    ...notification,
    actionUrl:
      notification.actionUrl.startsWith("/") &&
      !notification.actionUrl.startsWith("//")
        ? notification.actionUrl
        : "/notifications",
  };
}

export function getUnreadNotificationCount() {
  return apiClient.get<ApiUnreadNotificationCount>(
    "/notifications/unread-count/",
    { requiresAuth: true },
  );
}

export function markNotificationRead(id: string) {
  return apiClient.post<ApiNotification>(
    `/notifications/${id}/read/`,
    { requiresAuth: true },
  );
}

export function markAllNotificationsRead() {
  return apiClient.post<{ updatedCount: number; unreadCount: number }>(
    "/notifications/read-all/",
    { requiresAuth: true },
  );
}
