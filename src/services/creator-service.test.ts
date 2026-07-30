import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patch } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}));
vi.mock("@/services/api-client", () => ({
  apiClient: { get, post, patch },
}));

import {
  getCreatorDrafts,
  getCreatorProfile,
  getCreatorUploads,
  submitCreatorTrack,
  updateCreatorDraft,
} from "@/services/creator-service";

describe("creator service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses protected creator list and workflow endpoints", async () => {
    get.mockResolvedValue({});
    post.mockResolvedValue({});
    patch.mockResolvedValue({});

    await getCreatorProfile();
    await getCreatorDrafts();
    await getCreatorUploads();
    await submitCreatorTrack("draft-track");
    await updateCreatorDraft("draft-track", { titleNe: "नयाँ शीर्षक" });

    expect(get).toHaveBeenNthCalledWith(1, "/creator/profile/", {
      requiresAuth: true,
    });
    expect(get).toHaveBeenNthCalledWith(2, "/creator/tracks/drafts/", {
      query: { pageSize: 50 },
      requiresAuth: true,
    });
    expect(get).toHaveBeenNthCalledWith(3, "/creator/uploads/", {
      query: { pageSize: 50 },
      requiresAuth: true,
    });
    expect(post).toHaveBeenCalledWith(
      "/creator/tracks/draft-track/submit/",
      { requiresAuth: true },
    );
    expect(patch).toHaveBeenCalledWith(
      "/creator/tracks/draft-track/metadata/",
      { body: { titleNe: "नयाँ शीर्षक" }, requiresAuth: true },
    );
  });
});
