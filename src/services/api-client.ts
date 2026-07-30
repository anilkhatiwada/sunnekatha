import { environment } from "@/config/environment";
import { ApiError, normalizeApiError } from "@/services/api-error";
import {
  getAuthSessionAdapter,
  type AuthSessionAdapter,
} from "@/services/auth-session";

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue | QueryValue[]>;
type RequestBody = Record<string, unknown> | unknown[] | BodyInit;

export interface ApiRequestOptions<TBody = never> {
  body?: TBody;
  headers?: HeadersInit;
  query?: QueryParams;
  signal?: AbortSignal;
  requiresAuth?: boolean;
}

interface InternalRequestOptions<TBody> extends ApiRequestOptions<TBody> {
  hasRetriedAuthentication?: boolean;
}

interface ApiClientDependencies {
  fetch: typeof fetch;
  getAuthSession: () => AuthSessionAdapter;
}

const browserFetch: typeof fetch = (...args) => globalThis.fetch(...args);

export class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;

  constructor(
    private readonly baseUrl: string,
    private readonly timeoutMs: number,
    private readonly dependencies: ApiClientDependencies = {
      fetch: browserFetch,
      getAuthSession: getAuthSessionAdapter,
    },
  ) {}

  get<TResponse>(
    path: string,
    options?: ApiRequestOptions,
  ): Promise<TResponse> {
    return this.request<TResponse>("GET", path, options);
  }

  post<TResponse, TBody extends RequestBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("POST", path, options);
  }

  put<TResponse, TBody extends RequestBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("PUT", path, options);
  }

  patch<TResponse, TBody extends RequestBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("PATCH", path, options);
  }

  delete<TResponse = void, TBody extends RequestBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("DELETE", path, options);
  }

  private async request<
    TResponse,
    TBody extends RequestBody = never,
  >(
    method: string,
    path: string,
    options: InternalRequestOptions<TBody> = {},
  ): Promise<TResponse> {
    const controller = new AbortController();
    let didTimeout = false;
    const timeoutId = setTimeout(() => {
      didTimeout = true;
      controller.abort();
    }, this.timeoutMs);
    const signal = combineSignals(options.signal, controller.signal);
    const authSession = this.dependencies.getAuthSession();
    const accessToken = options.requiresAuth
      ? authSession.getAccessToken()
      : null;
    const { body, contentType } = serializeBody(options.body);

    try {
      const response = await this.dependencies.fetch(
        this.createUrl(path, options.query),
        {
          method,
          signal,
          headers: {
            Accept: "application/json",
            ...(contentType ? { "Content-Type": contentType } : {}),
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
            ...options.headers,
          },
          body,
        },
      );

      if (
        response.status === 401 &&
        options.requiresAuth &&
        !options.hasRetriedAuthentication &&
        (await this.refreshAuthentication())
      ) {
        return this.request<TResponse, TBody>(method, path, {
          ...options,
          hasRetriedAuthentication: true,
        });
      }

      if (!response.ok) {
        throw await normalizeApiError(undefined, response);
      }

      if (response.status === 204) return undefined as TResponse;
      return (await response.json()) as TResponse;
    } catch (error) {
      if (didTimeout) {
        throw new ApiError({
          code: "request_timeout",
          message: "सर्भरले समयमा जवाफ दिएन। फेरि प्रयास गर्नुहोस्।",
          cause: error,
        });
      }
      throw await normalizeApiError(error);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private createUrl(path: string, query?: QueryParams) {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    const url = new URL(`${this.baseUrl}${normalizedPath}`);

    for (const [key, rawValue] of Object.entries(query ?? {})) {
      const values = Array.isArray(rawValue) ? rawValue : [rawValue];
      for (const value of values) {
        if (value !== null && value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      }
    }

    return url;
  }

  private async refreshAuthentication() {
    if (!this.refreshPromise) {
      const authSession = this.dependencies.getAuthSession();
      this.refreshPromise = authSession
        .refreshAccessToken()
        .then((tokens) => {
          if (!tokens?.access) return false;
          authSession.setTokens(tokens);
          return true;
        })
        .catch(() => false)
        .finally(() => {
          this.refreshPromise = null;
        });
    }

    const didRefresh = await this.refreshPromise;
    if (!didRefresh) {
      this.dependencies.getAuthSession().onAuthenticationFailure();
    }
    return didRefresh;
  }
}

function serializeBody(body: RequestBody | undefined) {
  if (body === undefined) return { body: undefined, contentType: null };
  if (
    typeof body === "string" ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof Blob ||
    body instanceof ArrayBuffer
  ) {
    return { body, contentType: null };
  }
  return {
    body: JSON.stringify(body),
    contentType: "application/json",
  };
}

function combineSignals(
  externalSignal: AbortSignal | undefined,
  timeoutSignal: AbortSignal,
) {
  if (!externalSignal) return timeoutSignal;
  return AbortSignal.any([externalSignal, timeoutSignal]);
}

export const apiClient = new ApiClient(
  environment.apiBaseUrl,
  environment.apiTimeoutMs,
);
