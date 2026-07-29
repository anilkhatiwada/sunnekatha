import type { ApiErrorResponse, ApiFieldErrors } from "@/types";

const DEFAULT_ERROR_MESSAGE = "अनुरोध पूरा गर्न सकिएन।";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly fieldErrors: ApiFieldErrors;
  readonly retryAfterSeconds: number | null;
  readonly cause?: unknown;

  constructor({
    message = DEFAULT_ERROR_MESSAGE,
    status = null,
    code = "unknown_error",
    fieldErrors = {},
    retryAfterSeconds = null,
    cause,
  }: {
    message?: string;
    status?: number | null;
    code?: string;
    fieldErrors?: ApiFieldErrors;
    retryAfterSeconds?: number | null;
    cause?: unknown;
  } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.retryAfterSeconds = retryAfterSeconds;
    this.cause = cause;
  }
}

export async function normalizeApiError(
  error: unknown,
  response?: Response,
): Promise<ApiError> {
  if (error instanceof ApiError) return error;

  if (response) {
    const payload = await readErrorPayload(response);
    return new ApiError({
      status: response.status,
      code: payload.code ?? `http_${response.status}`,
      message: payload.detail ?? getStatusMessage(response.status),
      fieldErrors: payload.errors ?? {},
      retryAfterSeconds: parseRetryAfter(response.headers.get("Retry-After")),
      cause: error,
    });
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return new ApiError({
      code: "request_aborted",
      message: "अनुरोध रद्द भयो।",
      cause: error,
    });
  }

  if (error instanceof TypeError) {
    return new ApiError({
      code: "network_error",
      message: "सर्भरसँग जडान हुन सकेन।",
      cause: error,
    });
  }

  return new ApiError({
    message: error instanceof Error ? error.message : DEFAULT_ERROR_MESSAGE,
    cause: error,
  });
}

async function readErrorPayload(response: Response): Promise<ApiErrorResponse> {
  try {
    const payload: unknown = await response.clone().json();
    if (!payload || typeof payload !== "object") return {};

    const candidate = payload as Record<string, unknown>;
    return {
      detail:
        typeof candidate.detail === "string" ? candidate.detail : undefined,
      code: typeof candidate.code === "string" ? candidate.code : undefined,
      errors: normalizeFieldErrors(candidate.errors ?? candidate),
    };
  } catch {
    return {};
  }
}

function normalizeFieldErrors(value: unknown): ApiFieldErrors {
  if (!value || typeof value !== "object") return {};

  return Object.fromEntries(
    Object.entries(value).flatMap(([field, messages]) => {
      if (field === "detail" || field === "code") return [];
      if (typeof messages === "string") return [[field, [messages]]];
      if (Array.isArray(messages)) {
        return [[field, messages.filter((item): item is string => typeof item === "string")]];
      }
      return [];
    }),
  );
}

function getStatusMessage(status: number) {
  if (status === 401) return "कृपया फेरि साइन इन गर्नुहोस्।";
  if (status === 403) return "यो कार्य गर्न अनुमति छैन।";
  if (status === 404) return "मागिएको सामग्री भेटिएन।";
  if (status === 429) return "धेरै अनुरोध भए। केहीबेरपछि फेरि प्रयास गर्नुहोस्।";
  if (status >= 500) return "सर्भरमा समस्या भयो।";
  return DEFAULT_ERROR_MESSAGE;
}

function parseRetryAfter(value: string | null) {
  if (!value) return null;
  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds >= 0) return seconds;

  const retryDate = Date.parse(value);
  if (Number.isNaN(retryDate)) return null;
  return Math.max(0, Math.ceil((retryDate - Date.now()) / 1000));
}
