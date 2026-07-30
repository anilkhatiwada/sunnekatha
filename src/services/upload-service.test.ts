import { beforeEach, describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/services/api-client", () => ({
  apiClient: { post },
}));

import {
  requestDirectUpload,
  uploadCreatorFile,
  uploadFileDirectly,
} from "@/services/upload-service";

describe("direct upload service", () => {
  beforeEach(() => {
    post.mockReset();
    vi.unstubAllGlobals();
  });

  it("requests server-controlled signing metadata", async () => {
    post.mockResolvedValue({ id: "session" });
    const payload = {
      uploadType: "cover_image" as const,
      originalFilename: "cover.jpg",
      contentType: "image/jpeg",
      expectedSize: 42,
    };

    await requestDirectUpload(payload);

    expect(post).toHaveBeenCalledWith("/uploads/", {
      body: payload,
      requiresAuth: true,
    });
  });

  it("posts every signed field and the file directly to S3", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["image"], "cover.jpg", { type: "image/jpeg" });

    await uploadFileDirectly(
      { url: "https://bucket.example/", fields: { key: "safe/key", policy: "p" } },
      file,
    );

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = init.body as FormData;
    expect(fetchMock).toHaveBeenCalledWith("https://bucket.example/", {
      method: "POST",
      body,
    });
    expect(body.get("key")).toBe("safe/key");
    expect(body.get("policy")).toBe("p");
    expect(body.get("file")).toBe(file);
  });

  it("confirms only after the direct upload succeeds", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
    const session = {
      id: "session-id",
      upload: { url: "https://bucket.example/", fields: {} },
    };
    post
      .mockResolvedValueOnce(session)
      .mockResolvedValueOnce({ ...session, status: "confirmed" });

    const result = await uploadCreatorFile(
      new File(["audio"], "story.mp3", { type: "audio/mpeg" }),
      "audio_master",
    );

    expect(post).toHaveBeenNthCalledWith(
      2,
      "/uploads/session-id/confirm/",
      { requiresAuth: true },
    );
    expect(result.status).toBe("confirmed");
  });
});
