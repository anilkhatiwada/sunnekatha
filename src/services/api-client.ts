import { environment } from "@/config/environment";
import { normalizeApiError } from "@/services/api-error";
import { getAuthSessionAdapter } from "@/services/auth-session";

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue | QueryValue[]>;

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

class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;

  constructor(
    private readonly baseUrl: string,
    private readonly timeoutMs: number,
  ) {}

  get<TResponse>(
    path: string,
    options?: ApiRequestOptions,
  ): Promise<TResponse> {
    return this.request<TResponse>("GET", path, options);
  }

  post<TResponse, TBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("POST", path, options);
  }

  put<TResponse, TBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("PUT", path, options);
  }

  patch<TResponse, TBody = never>(
    path: string,
    options?: ApiRequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.request<TResponse, TBody>("PATCH", path, options);
  }

  delete<TResponse = void>(
    path: string,
    options?: ApiRequestOptions,
  ): Promise<TResponse> {
    return this.request<TResponse>("DELETE", path, options);
  }

  private async request<TResponse, TBody = never>(
    method: string,
    path: string,
    options: InternalRequestOptions<TBody> = {},
  ): Promise<TResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);
    const signal = combineSignals(options.signal, controller.signal);
    const authSession = getAuthSessionAdapter();
    const accessToken = options.requiresAuth
      ? authSession.getAccessToken()
      : null;

    try {
      const response = await fetch(this.createUrl(path, options.query), {
        method,
        signal,
        headers: {
          Accept: "application/json",
          ...(options.body === undefined
            ? {}
            : { "Content-Type": "application/json" }),
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...options.headers,
        },
        body:
          options.body === undefined
            ? undefined
            : JSON.stringify(options.body),
      });

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
      this.refreshPromise = getAuthSessionAdapter()
        .refreshAccessToken()
        .then((tokens) => {
          if (!tokens?.access) return false;
          getAuthSessionAdapter().setTokens(tokens);
          return true;
        })
        .catch(() => false)
        .finally(() => {
          this.refreshPromise = null;
        });
    }

    const didRefresh = await this.refreshPromise;
    if (!didRefresh) {
      getAuthSessionAdapter().onAuthenticationFailure();
    }
    return didRefresh;
  }
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
