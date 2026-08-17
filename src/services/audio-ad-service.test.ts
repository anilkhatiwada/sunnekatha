import { beforeEach, describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/services/api-client", () => ({ apiClient: { post } }));

import {
  getAudioAdvertisementSessionId,
  getNextAudioAdvertisement,
  recordAudioAdvertisementStarted,
} from "@/services/audio-ad-service";

describe("audio advertisement service", () => {
  beforeEach(() => {
    post.mockReset();
    window.localStorage.clear();
  });

  it("keeps one anonymous cadence session on the device", () => {
    const first = getAudioAdvertisementSessionId();
    const second = getAudioAdvertisementSessionId();

    expect(first).toBe(second);
    expect(first).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("uses eligibility and actual-start endpoints", async () => {
    post.mockResolvedValue({ advertisement: null, reason: "frequency_not_reached" });
    const request = {
      sessionId: "8ebc26b4-2f30-4dc0-a7f4-6c12d3523951",
      playbackSequence: 3,
      trackId: "6ad81349-b0c5-4fe1-b62b-7de570708e1f",
      source: "playlist" as const,
    };

    await getNextAudioAdvertisement(request);
    await recordAudioAdvertisementStarted(
      "4342d825-98f6-47de-a45e-313afc079417",
      request,
    );

    expect(post).toHaveBeenNthCalledWith(1, "/audio-ads/next/", {
      body: request,
      requiresAuth: true,
    });
    expect(post).toHaveBeenNthCalledWith(
      2,
      "/audio-ads/4342d825-98f6-47de-a45e-313afc079417/started/",
      { body: request, requiresAuth: true },
    );
  });
});
