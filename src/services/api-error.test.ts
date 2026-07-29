import { describe, expect, it } from "vitest";

import { ApiError, normalizeApiError } from "@/services/api-error";
import { queryKeys } from "@/services/query-keys";

describe("API boundary", () => {
  it("normalizes DRF detail and field errors", async () => {
    const response = new Response(
      JSON.stringify({
        detail: "Validation failed",
        code: "invalid",
        errors: { email: ["Enter a valid email."] },
      }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" },
      },
    );

    const error = await normalizeApiError(undefined, response);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 400,
      code: "invalid",
      message: "Validation failed",
      fieldErrors: { email: ["Enter a valid email."] },
    });
  });

  it("creates stable, scoped TanStack Query keys", () => {
    expect(queryKeys.tracks.detail("premka-kavita")).toEqual([
      "tracks",
      "detail",
      "premka-kavita",
    ]);
    expect(
      queryKeys.explore.releases({ contentType: "poem", mood: "calm" }),
    ).toEqual([
      "explore",
      "releases",
      { contentType: "poem", mood: "calm" },
    ]);
  });

  it("normalizes rate-limit retry metadata", async () => {
    const response = new Response(
      JSON.stringify({
        detail: "Request was throttled.",
        code: "throttled",
      }),
      {
        status: 429,
        headers: {
          "Content-Type": "application/json",
          "Retry-After": "30",
        },
      },
    );

    await expect(normalizeApiError(undefined, response)).resolves.toMatchObject({
      status: 429,
      code: "throttled",
      retryAfterSeconds: 30,
    });
  });
});
