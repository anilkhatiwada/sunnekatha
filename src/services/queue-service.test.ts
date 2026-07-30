import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, put, patch, remove } = vi.hoisted(() => ({
  get: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/services/api-client", () => ({
  apiClient: { get, put, patch, delete: remove },
}));

import {
  clearSynchronizedQueue,
  getCurrentQueue,
  replaceSynchronizedQueue,
  updateSynchronizedQueuePosition,
  updateSynchronizedQueueRepeat,
  updateSynchronizedQueueShuffle,
} from "@/services/queue-service";

describe("queue synchronization service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses the authenticated queue endpoints", async () => {
    get.mockResolvedValue({});
    put.mockResolvedValue({});
    patch.mockResolvedValue({});
    remove.mockResolvedValue(undefined);

    await getCurrentQueue();
    await replaceSynchronizedQueue({
      trackIds: ["a", "a", "b"],
      currentIndex: 1,
      positionSeconds: 20,
    });
    await updateSynchronizedQueuePosition({
      currentIndex: 2,
      positionSeconds: 30,
    });
    await updateSynchronizedQueueShuffle(true);
    await updateSynchronizedQueueRepeat("all");
    await clearSynchronizedQueue();

    expect(get).toHaveBeenCalledWith("/me/queue/", { requiresAuth: true });
    expect(put).toHaveBeenCalledWith("/me/queue/", {
      body: {
        trackIds: ["a", "a", "b"],
        currentIndex: 1,
        positionSeconds: 20,
      },
      requiresAuth: true,
    });
    expect(patch).toHaveBeenCalledWith("/me/queue/position/", {
      body: { currentIndex: 2, positionSeconds: 30 },
      requiresAuth: true,
    });
    expect(patch).toHaveBeenCalledWith("/me/queue/shuffle/", {
      body: { isShuffleEnabled: true },
      requiresAuth: true,
    });
    expect(patch).toHaveBeenCalledWith("/me/queue/repeat/", {
      body: { repeatMode: "all" },
      requiresAuth: true,
    });
    expect(remove).toHaveBeenCalledWith("/me/queue/", {
      requiresAuth: true,
    });
  });
});
