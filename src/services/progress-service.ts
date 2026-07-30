"use client";

import { environment } from "@/config/environment";
import { useLibraryStore } from "@/features/library/library-store";
import { apiClient } from "@/services/api-client";
import { hasStoredSession } from "@/services/auth-service";
import { mapListeningProgress } from "@/services/api-mappers";
import type { ApiListeningProgress, ListeningProgress } from "@/types";

export const PROGRESS_UPDATE_INTERVAL_SECONDS = 15;

export interface SaveProgressInput {
  trackId: string;
  progressSeconds: number;
  durationSeconds: number;
}

/**
 * Local-first progress boundary. A future Django adapter can sync the normalized
 * record after this immediate local write without changing player code.
 */
export function saveListeningProgress({
  trackId,
  progressSeconds,
  durationSeconds,
}: SaveProgressInput): ListeningProgress | null {
  const safeDuration = Math.max(0, durationSeconds);
  const safeProgress = Math.min(
    safeDuration,
    Math.max(0, progressSeconds),
  );

  if (safeProgress < 1 || safeDuration <= 0) {
    return null;
  }

  useLibraryStore
    .getState()
    .updateListeningProgress(trackId, safeProgress, safeDuration);

  const progress =
    useLibraryStore
      .getState()
      .listeningProgress.find((item) => item.trackId === trackId) ?? null;

  if (
    progress &&
    environment.apiMode === "remote" &&
    hasStoredSession()
  ) {
    void apiClient
      .put<
        ApiListeningProgress,
        { progressSeconds: number; durationSeconds: number }
      >(`/me/listening-progress/${trackId}/`, {
        body: {
          progressSeconds: safeProgress,
          durationSeconds: safeDuration,
        },
        requiresAuth: true,
      })
      .catch(() => {
        // Playback remains local-first; the next periodic update retries sync.
      });
  }

  return progress;
}

export function getSavedProgress(trackId: string) {
  return (
    useLibraryStore
      .getState()
      .listeningProgress.find((item) => item.trackId === trackId) ?? null
  );
}

export function getResumePosition(trackId: string) {
  const progress = getSavedProgress(trackId);

  return progress && !progress.isCompleted
    ? progress.progressSeconds
    : 0;
}

export function recordRecentlyPlayed(trackId: string) {
  useLibraryStore.getState().addRecentlyPlayed(trackId);
}

export async function getServerListeningProgress(trackId: string) {
  if (environment.apiMode !== "remote" || !hasStoredSession()) return null;
  try {
    const progress = await apiClient.get<ApiListeningProgress>(
      `/me/listening-progress/${trackId}/`,
      { requiresAuth: true },
    );
    const mapped = mapListeningProgress(progress);
    useLibraryStore.getState().updateListeningProgress(
      mapped.trackId,
      mapped.progressSeconds,
      mapped.durationSeconds,
    );
    return mapped;
  } catch {
    return null;
  }
}

export function markTrackCompleted(trackId: string) {
  if (environment.apiMode !== "remote" || !hasStoredSession()) {
    return Promise.resolve(null);
  }
  return apiClient
    .post<ApiListeningProgress>(
      `/me/listening-progress/${trackId}/complete/`,
      { requiresAuth: true },
    )
    .then(mapListeningProgress);
}

export function removeFromContinueListening(trackId: string) {
  return apiClient.delete<void>(
    `/me/listening-progress/${trackId}/remove/`,
    { requiresAuth: true },
  );
}
