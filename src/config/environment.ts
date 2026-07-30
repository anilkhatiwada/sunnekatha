export type ApiMode = "mock" | "remote";
export type AppEnvironment = "local" | "staging" | "production";

interface PublicEnvironmentSource {
  NEXT_PUBLIC_API_MODE?: string;
  NEXT_PUBLIC_API_BASE_URL?: string;
  NEXT_PUBLIC_API_TIMEOUT_MS?: string;
  NEXT_PUBLIC_APP_ENV?: string;
  NEXT_PUBLIC_GOOGLE_CLIENT_ID?: string;
}

const DEFAULT_MOCK_API_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_API_TIMEOUT_MS = 15_000;

export function createEnvironment(source: PublicEnvironmentSource) {
  const apiMode: ApiMode =
    source.NEXT_PUBLIC_API_MODE === "remote" ? "remote" : "mock";
  const configuredBaseUrl = source.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (apiMode === "remote" && !configuredBaseUrl) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is required when NEXT_PUBLIC_API_MODE=remote.",
    );
  }

  const timeout = Number(
    source.NEXT_PUBLIC_API_TIMEOUT_MS ?? DEFAULT_API_TIMEOUT_MS,
  );
  const candidate = {
    apiMode,
    apiBaseUrl: (
      configuredBaseUrl || DEFAULT_MOCK_API_BASE_URL
    ).replace(/\/+$/, ""),
    apiTimeoutMs: timeout,
    appEnvironment:
      source.NEXT_PUBLIC_APP_ENV === "staging" ||
      source.NEXT_PUBLIC_APP_ENV === "production"
        ? source.NEXT_PUBLIC_APP_ENV
        : "local",
    googleClientId: source.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? "",
  };

  try {
    const parsedUrl = new URL(candidate.apiBaseUrl);
    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
      throw new Error("Only HTTP and HTTPS API URLs are supported.");
    }
  } catch (error) {
    throw new Error(
      `Invalid public environment configuration: apiBaseUrl: ${
        error instanceof Error ? error.message : "Invalid URL"
      }`,
    );
  }
  if (
    !Number.isInteger(candidate.apiTimeoutMs) ||
    candidate.apiTimeoutMs <= 0 ||
    candidate.apiTimeoutMs > 120_000
  ) {
    throw new Error(
      "Invalid public environment configuration: apiTimeoutMs must be an integer between 1 and 120000.",
    );
  }
  if (
    candidate.appEnvironment === "production" &&
    candidate.apiMode === "remote" &&
    !candidate.apiBaseUrl.startsWith("https://")
  ) {
    throw new Error(
      "Invalid public environment configuration: Production API URLs must use HTTPS.",
    );
  }

  return Object.freeze(candidate);
}

export const environment = createEnvironment({
  NEXT_PUBLIC_API_MODE: process.env.NEXT_PUBLIC_API_MODE,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_API_TIMEOUT_MS: process.env.NEXT_PUBLIC_API_TIMEOUT_MS,
  NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
  NEXT_PUBLIC_GOOGLE_CLIENT_ID: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
});
