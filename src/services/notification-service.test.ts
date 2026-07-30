import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));
vi.mock("@/services/api-client", () => ({
  apiClient: { get, post },
}));

import {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/services/notification-service";

describe("notification service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads authenticated notifications and rejects external action links", async () => {
    get.mockResolvedValue({
      results: [{ id: "notification", actionUrl: "https://malicious.example/" }],
    });

    const notifications = await getNotifications();

    expect(get).toHaveBeenCalledWith("/notifications/", {
      query: { pageSize: 50 },
      requiresAuth: true,
    });
    expect(notifications[0].actionUrl).toBe("/notifications");
  });

  it("uses unread and read mutation endpoints", async () => {
    get.mockResolvedValue({ unreadCount: 2 });
    post.mockResolvedValue({});

    await getUnreadNotificationCount();
    await markNotificationRead("item");
    await markAllNotificationsRead();

    expect(get).toHaveBeenCalledWith("/notifications/unread-count/", {
      requiresAuth: true,
    });
    expect(post).toHaveBeenNthCalledWith(
      1,
      "/notifications/item/read/",
      { requiresAuth: true },
    );
    expect(post).toHaveBeenNthCalledWith(
      2,
      "/notifications/read-all/",
      { requiresAuth: true },
    );
  });
});
