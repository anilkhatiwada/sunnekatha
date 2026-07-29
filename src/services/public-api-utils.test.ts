import { describe, expect, it } from "vitest";

import { ApiError } from "@/services/api-error";
import {
  nullOnNotFound,
  unwrapPage,
} from "@/services/public-api-utils";

describe("public API helpers", () => {
  it("unwraps DRF page-number pagination without changing item order", () => {
    expect(
      unwrapPage({
        count: 2,
        next: null,
        previous: null,
        results: ["पहिलो", "दोस्रो"],
      }),
    ).toEqual(["पहिलो", "दोस्रो"]);
  });

  it("turns only HTTP 404 responses into a missing detail", async () => {
    await expect(
      nullOnNotFound(
        Promise.reject(new ApiError({ status: 404, code: "not_found" })),
      ),
    ).resolves.toBeNull();

    await expect(
      nullOnNotFound(
        Promise.reject(new ApiError({ status: 500, code: "server_error" })),
      ),
    ).rejects.toMatchObject({ status: 500 });
  });
});
