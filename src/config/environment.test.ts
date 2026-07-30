import { describe, expect, it } from "vitest";

import { createEnvironment } from "@/config/environment";

describe("public environment configuration", () => {
  it("normalizes a configured remote API URL", () => {
    expect(
      createEnvironment({
        NEXT_PUBLIC_API_MODE: "remote",
        NEXT_PUBLIC_API_BASE_URL: "https://api.sunnekatha.example/api/v1///",
        NEXT_PUBLIC_API_TIMEOUT_MS: "20000",
        NEXT_PUBLIC_APP_ENV: "staging",
      }),
    ).toEqual({
      apiMode: "remote",
      apiBaseUrl: "https://api.sunnekatha.example/api/v1",
      apiTimeoutMs: 20_000,
      appEnvironment: "staging",
      googleClientId: "",
    });
  });

  it("requires a base URL in remote mode", () => {
    expect(() =>
      createEnvironment({ NEXT_PUBLIC_API_MODE: "remote" }),
    ).toThrow("NEXT_PUBLIC_API_BASE_URL is required");
  });

  it("rejects an insecure production API URL", () => {
    expect(() =>
      createEnvironment({
        NEXT_PUBLIC_API_MODE: "remote",
        NEXT_PUBLIC_API_BASE_URL: "http://api.sunnekatha.example/api/v1",
        NEXT_PUBLIC_APP_ENV: "production",
      }),
    ).toThrow("Production API URLs must use HTTPS");
  });
});
