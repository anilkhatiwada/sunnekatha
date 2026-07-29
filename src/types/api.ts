export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PageNumberPaginationParams {
  page?: number;
  pageSize?: number;
}

export interface CursorPaginatedResponse<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CursorPaginationParams {
  cursor?: string;
  pageSize?: number;
}

export interface ApiFieldErrors {
  [field: string]: string[];
}

export interface ApiErrorResponse {
  detail?: string;
  code?: string;
  errors?: ApiFieldErrors;
}

export interface AuthTokens {
  access: string;
  refresh?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: AuthenticatedUser;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  displayName: string;
}

export interface RefreshTokenRequest {
  refresh: string;
}

export interface RefreshTokenResponse {
  access: string;
  refresh?: string;
}
