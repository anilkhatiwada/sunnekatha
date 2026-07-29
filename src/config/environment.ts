export type ApiMode = "mock" | "remote";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_API_TIMEOUT_MS = 15_000;

function readApiMode(value: string | undefined): ApiMode {
  return value === "remote" ? "remote" : "mock";
}

function readPositiveInteger(value: string | undefined, fallback: number) {
  const parsedValue = Number(value);
  return Number.isInteger(parsedValue) && parsedValue > 0
    ? parsedValue
    : fallback;
}

function normalizeBaseUrl(value: string | undefined) {
  return (value?.trim() || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export const environment = Object.freeze({
  apiMode: readApiMode(process.env.NEXT_PUBLIC_API_MODE),
  apiBaseUrl: normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
  apiTimeoutMs: readPositiveInteger(
    process.env.NEXT_PUBLIC_API_TIMEOUT_MS,
    DEFAULT_API_TIMEOUT_MS,
  ),
});
