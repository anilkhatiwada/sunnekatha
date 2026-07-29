import { apiClient } from "@/services/api-client";
import type { ApiStreamResponse } from "@/types/backend-api";

export function getTrackStream(
  slug: string,
  quality: "auto" | "low" | "high" = "auto",
) {
  return apiClient.get<ApiStreamResponse>(`/tracks/${slug}/stream/`, {
    query: { quality },
    // The endpoint is public for free tracks and uses the token when available.
    requiresAuth: true,
  });
}
