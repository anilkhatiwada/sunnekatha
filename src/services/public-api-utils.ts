import { ApiError } from "@/services/api-error";
import type { PaginatedResponse } from "@/types";

export function unwrapPage<T>(payload: PaginatedResponse<T>): T[] {
  return payload.results;
}

export async function nullOnNotFound<T>(
  request: Promise<T>,
): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
